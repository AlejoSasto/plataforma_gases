"""Entrenamiento de modelos secuenciales (PyTorch)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Optional

import mlflow
import numpy as np
import torch
import torch.nn as nn
from sqlalchemy.orm import Session
from torch.utils.data import DataLoader, TensorDataset

from ml_core.features.sequences import build_sequences
from ml_core.models.architectures import build_sequence_model
from ml_core.models.metrics import (
    classification_metrics,
    lead_time_metrics,
    merge_metric_blocks,
    regression_metrics,
)
from ml_core.models.registry import applicability_for, get_spec
from ml_core.models.train_tabular import TrainingResult


def _train_one(
    model: nn.Module,
    *,
    x_train: np.ndarray,
    y_class_train: np.ndarray,
    y_reg_train: np.ndarray,
    y_lead_train: np.ndarray,
    x_test: np.ndarray,
    y_class_test: np.ndarray,
    y_reg_test: np.ndarray,
    y_lead_test: np.ndarray,
    task: str,
    epochs: int = 8,
    batch_size: int = 64,
    lr: float = 1e-3,
) -> tuple[nn.Module, dict[str, Any]]:
    device = torch.device("cpu")
    model = model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    # Normalizar features por canal (train)
    mean = x_train.mean(axis=(0, 1), keepdims=True)
    std = x_train.std(axis=(0, 1), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    x_train_n = ((x_train - mean) / std).astype(np.float32)
    x_test_n = ((x_test - mean) / std).astype(np.float32)

    pos = float(max(1, int(y_class_train.sum())))
    neg = float(max(1, int(len(y_class_train) - pos)))
    pos_weight = torch.tensor([neg / pos], dtype=torch.float32, device=device)
    bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    mse = nn.MSELoss()

    # Escalar target de regresión
    y_reg_mean = float(np.nanmean(y_reg_train)) if len(y_reg_train) else 0.0
    y_reg_std = float(np.nanstd(y_reg_train)) if len(y_reg_train) else 1.0
    if y_reg_std < 1e-6:
        y_reg_std = 1.0
    y_reg_train_n = ((y_reg_train - y_reg_mean) / y_reg_std).astype(np.float32)
    y_reg_test_n = ((y_reg_test - y_reg_mean) / y_reg_std).astype(np.float32)

    xt = torch.tensor(x_train_n, dtype=torch.float32)
    yc = torch.tensor(y_class_train, dtype=torch.float32)
    yr = torch.tensor(y_reg_train_n, dtype=torch.float32)
    ds = TensorDataset(xt, yc, yr)
    loader = DataLoader(ds, batch_size=min(batch_size, max(1, len(ds))), shuffle=True)

    model.train()
    for _ in range(epochs):
        for xb, ycb, yrb in loader:
            xb, ycb, yrb = xb.to(device), ycb.to(device), yrb.to(device)
            opt.zero_grad()
            out = model(xb)
            loss = torch.zeros((), device=device)
            if "logits" in out and task in ("classification", "both"):
                loss = loss + bce(out["logits"], ycb)
            if "reg" in out and task in ("regression", "both"):
                loss = loss + mse(out["reg"], yrb)
            if loss.detach().item() == 0.0:
                continue
            loss.backward()
            opt.step()

    model.eval()
    thr = 0.5
    with torch.no_grad():
        xte = torch.tensor(x_test_n, dtype=torch.float32).to(device)
        out = model(xte)
        clf_m = reg_m = lead_m = None
        if "logits" in out and task in ("classification", "both"):
            probs = torch.sigmoid(out["logits"]).cpu().numpy()
            thr = min(0.5, max(0.15, pos / (pos + neg)))
            preds = (probs >= thr).astype(int)
            clf_m = classification_metrics(y_class_test, preds)
            lead_m = lead_time_metrics(y_lead_test, preds)
        if "reg" in out and task in ("regression", "both"):
            yhat_n = out["reg"].cpu().numpy()
            yhat = yhat_n * y_reg_std + y_reg_mean
            reg_m = regression_metrics(y_reg_test, yhat)

    model._pg_norm_mean = mean  # type: ignore[attr-defined]
    model._pg_norm_std = std  # type: ignore[attr-defined]
    model._pg_reg_mean = y_reg_mean  # type: ignore[attr-defined]
    model._pg_reg_std = y_reg_std  # type: ignore[attr-defined]
    model._pg_cls_threshold = float(thr)  # type: ignore[attr-defined]

    return model, {
        "clf": clf_m,
        "reg": reg_m,
        "lead": lead_m,
        "norm_mean": mean,
        "norm_std": std,
        "reg_mean": y_reg_mean,
        "reg_std": y_reg_std,
        "cls_threshold": float(thr),
    }


def train_sequence_algorithms(
    db: Session,
    algorithms: list[str],
    *,
    task: str = "both",
    dataset_version: str = "gas_readings",
    params: Optional[dict[str, Any]] = None,
    triggered_by_user_id: int | None = None,
) -> list[TrainingResult]:
    params = dict(params or {})
    max_rows = params.get("max_rows")
    test_months = int(params.get("test_months", 3))
    lookback = int(params.get("lookback_steps") or 20)
    horizon = float(params.get("horizon_minutes", 7.5))
    epochs = int(params.get("epochs", 12))

    seq = build_sequences(
        db,
        max_rows=max_rows,
        test_months=test_months,
        lookback_steps=lookback,
        horizon_minutes=horizon,
    )
    if seq.n_train < 10 or seq.n_test < 5:
        raise ValueError(
            f"Secuencias insuficientes (train={seq.n_train}, test={seq.n_test})"
        )

    n_features = seq.x_train.shape[-1]
    results: list[TrainingResult] = []

    for algo in algorithms:
        spec = get_spec(algo)
        if spec.family != "sequence":
            continue
        model = build_sequence_model(algo, n_features=n_features, task=task)
        trained, blocks = _train_one(
            model,
            x_train=seq.x_train,
            y_class_train=seq.y_class_train,
            y_reg_train=seq.y_reg_train,
            y_lead_train=seq.y_lead_train,
            x_test=seq.x_test,
            y_class_test=seq.y_class_test,
            y_reg_test=seq.y_reg_test,
            y_lead_test=seq.y_lead_test,
            task=task,
            epochs=epochs,
        )
        metrics = merge_metric_blocks(
            classification=blocks["clf"],
            regression=blocks["reg"],
            temporal=blocks["lead"] if spec.uses_lead else None,
            applicable=applicability_for(algo, task),
        )
        hp = {
            "dataset_version": dataset_version,
            "task": task,
            "family": "sequence",
            "framework": "torch",
            "lookback_steps": lookback,
            "horizon_minutes": horizon,
            "n_features": n_features,
            "epochs": epochs,
            "n_train": seq.n_train,
            "n_test": seq.n_test,
            "triggered_by_user_id": triggered_by_user_id,
            "input_shape": [lookback, n_features],
            "cls_threshold": blocks.get("cls_threshold", 0.5),
        }

        with mlflow.start_run(run_name=algo) as run:
            mlflow.log_params({k: str(v) for k, v in hp.items()})
            flat = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
            if flat:
                mlflow.log_metrics(flat)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "model.pt"
                card = Path(tmp) / "model_card.json"
                torch.save(
                    {
                        "state_dict": trained.state_dict(),
                        "algorithm": algo,
                        "task": task,
                        "n_features": n_features,
                        "lookback_steps": lookback,
                        "hidden": 64,
                        "norm_mean": blocks.get("norm_mean"),
                        "norm_std": blocks.get("norm_std"),
                        "reg_mean": blocks.get("reg_mean"),
                        "reg_std": blocks.get("reg_std"),
                        "cls_threshold": blocks.get("cls_threshold", 0.5),
                    },
                    path,
                )
                card.write_text(
                    json.dumps({"algorithm": algo, "task": task, "framework": "torch"}),
                    encoding="utf-8",
                )
                mlflow.log_artifact(str(path), artifact_path="model")
                mlflow.log_artifact(str(card), artifact_path="model")
            artifact_uri = f"{run.info.artifact_uri}/model"
            results.append(
                TrainingResult(
                    algorithm=algo,
                    metrics=metrics,
                    params=hp,
                    mlflow_run_id=run.info.run_id,
                    artifact_uri=artifact_uri,
                    model=trained,
                )
            )
    return results
