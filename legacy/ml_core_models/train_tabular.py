"""Entrenamiento de modelos tabulares (sklearn / XGBoost)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy.orm import Session
from xgboost import XGBClassifier, XGBRegressor

from legacy.ml_core_features.build_features import FEATURE_COLUMNS, LABEL_COLUMN, build_features
from legacy.ml_core_features.targets import add_future_targets
from legacy.ml_core_models.metrics import (
    classification_metrics,
    lead_time_metrics,
    merge_metric_blocks,
    regression_metrics,
)
from legacy.ml_core_models.registry import applicability_for, get_spec


@dataclass
class TrainingResult:
    algorithm: str
    metrics: dict[str, Any]
    params: dict[str, Any]
    mlflow_run_id: str
    artifact_uri: str
    model: Any = field(repr=False, default=None)


def _xy_class(train, test):
    cols = FEATURE_COLUMNS
    return (
        np.nan_to_num(train[cols].to_numpy(dtype=float), nan=0.0),
        train[LABEL_COLUMN].to_numpy(dtype=int),
        np.nan_to_num(test[cols].to_numpy(dtype=float), nan=0.0),
        test[LABEL_COLUMN].to_numpy(dtype=int),
    )


def _xy_reg(train, test):
    cols = FEATURE_COLUMNS
    tr = train.dropna(subset=["y_reg"])
    te = test.dropna(subset=["y_reg"])
    return (
        np.nan_to_num(tr[cols].to_numpy(dtype=float), nan=0.0),
        tr["y_reg"].to_numpy(dtype=float),
        np.nan_to_num(te[cols].to_numpy(dtype=float), nan=0.0),
        te["y_reg"].to_numpy(dtype=float),
        te,
    )


def _log_model(name: str, model: Any, params: dict, metrics: dict, *, xgb: bool) -> TrainingResult:
    with mlflow.start_run(run_name=name) as run:
        mlflow.log_params({k: str(v) for k, v in params.items()})
        flat = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
        if flat:
            mlflow.log_metrics(flat)
        if xgb:
            mlflow.xgboost.log_model(model, artifact_path="model")
        else:
            mlflow.sklearn.log_model(model, artifact_path="model")
        return TrainingResult(
            algorithm=name,
            metrics=metrics,
            params=params,
            mlflow_run_id=run.info.run_id,
            artifact_uri=f"{run.info.artifact_uri}/model",
            model=model,
        )


def _classifier(algorithm: str, scale_pos: float):
    if algorithm == "logistic_regression":
        return LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"), {
            "max_iter": 1000
        }
    if algorithm == "decision_tree":
        return DecisionTreeClassifier(
            class_weight="balanced", random_state=42, max_depth=12
        ), {"max_depth": 12}
    if algorithm == "random_forest":
        return RandomForestClassifier(
            n_estimators=150, class_weight="balanced", random_state=42, n_jobs=-1
        ), {"n_estimators": 150}
    if algorithm == "svm":
        # SVC con probabilidad (necesario para risk); dataset acotado en UI
        return SVC(
            kernel="rbf", class_weight="balanced", probability=True, random_state=42
        ), {"kernel": "rbf"}
    if algorithm == "mlp":
        return MLPClassifier(
            hidden_layer_sizes=(64, 32), max_iter=150, random_state=42
        ), {"hidden_layer_sizes": "(64,32)"}
    if algorithm == "xgboost":
        return XGBClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            eval_metric="logloss",
            scale_pos_weight=scale_pos,
            random_state=42,
            n_jobs=-1,
        ), {"n_estimators": 150, "max_depth": 6}
    raise ValueError(algorithm)


def _regressor(algorithm: str):
    if algorithm == "random_forest":
        return RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1), {
            "n_estimators": 150
        }
    if algorithm == "mlp":
        return MLPRegressor(
            hidden_layer_sizes=(64, 32), max_iter=150, random_state=42
        ), {"hidden_layer_sizes": "(64,32)"}
    if algorithm == "xgboost":
        return XGBRegressor(
            n_estimators=150, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1
        ), {"n_estimators": 150}
    return None, {}


def train_tabular_algorithms(
    db: Session,
    algorithms: list[str],
    *,
    task: str = "classification",
    dataset_version: str = "gas_readings",
    params: Optional[dict[str, Any]] = None,
    triggered_by_user_id: int | None = None,
) -> list[TrainingResult]:
    params = dict(params or {})
    max_rows = params.get("max_rows")
    test_months = int(params.get("test_months", 3))
    horizon = float(params.get("horizon_minutes", 7.5))

    split = build_features(db, max_rows=max_rows, test_months=test_months)
    if split.train.empty or split.test.empty:
        raise ValueError("No hay suficientes datos tabulares para entrenar/testear")

    train = add_future_targets(split.train, horizon_minutes=horizon)
    test = add_future_targets(split.test, horizon_minutes=horizon)
    x_tr_c, y_tr_c, x_te_c, y_te_c = _xy_class(train, test)
    pos = int(y_tr_c.sum())
    neg = int(len(y_tr_c) - pos)
    scale_pos = (neg / pos) if pos > 0 else 1.0

    results: list[TrainingResult] = []
    for algo in algorithms:
        spec = get_spec(algo)
        if spec.family != "tabular":
            continue

        do_clf = task in ("classification", "both") and (
            "classification" in spec.tasks or "both" in spec.tasks
        )
        do_reg = task in ("regression", "both") and (
            "regression" in spec.tasks or "both" in spec.tasks
        )
        if not do_clf and not do_reg:
            continue

        clf_metrics = reg_metrics = lead_metrics = None
        model_obj: Any = None
        hp: dict[str, Any] = {
            "dataset_version": dataset_version,
            "task": task,
            "family": "tabular",
            "framework": spec.framework,
            "triggered_by_user_id": triggered_by_user_id,
        }

        if do_clf:
            model, model_hp = _classifier(algo, scale_pos)
            model.fit(x_tr_c, y_tr_c)
            y_pred = model.predict(x_te_c)
            clf_metrics = classification_metrics(y_te_c, y_pred)
            if "y_alert_lead" in test.columns:
                lead_metrics = lead_time_metrics(
                    test["y_alert_lead"].to_numpy(), y_pred
                )
            model_obj = model
            hp.update(model_hp)

        if do_reg:
            reg, reg_hp = _regressor(algo)
            if reg is not None:
                x_tr_r, y_tr_r, x_te_r, y_te_r, _ = _xy_reg(train, test)
                if len(y_tr_r) and len(y_te_r):
                    reg.fit(x_tr_r, y_tr_r)
                    reg_metrics = regression_metrics(y_te_r, reg.predict(x_te_r))
                    hp.update({f"reg_{k}": v for k, v in reg_hp.items()})
                    if task == "regression":
                        model_obj = reg

        if model_obj is None:
            continue

        metrics = merge_metric_blocks(
            classification=clf_metrics,
            regression=reg_metrics,
            temporal=lead_metrics if spec.uses_lead else None,
            applicable=applicability_for(algo, task),
        )
        results.append(
            _log_model(algo, model_obj, hp, metrics, xgb=(spec.framework == "xgboost"))
        )
    return results
