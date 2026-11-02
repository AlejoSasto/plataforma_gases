"""Tests unitarios de métricas thesis y targets temporales."""

from __future__ import annotations

import numpy as np
import pandas as pd

from legacy.ml_core_features.targets import (
    add_future_targets,
    horizon_steps_from_minutes,
    median_delta_minutes,
)
from legacy.ml_core_models.metrics import (
    apply_thesis_gates,
    classification_metrics,
    merge_metric_blocks,
    regression_metrics,
)
from legacy.ml_core_models.registry import MODEL_CATALOG, applicability_for


def test_classification_and_fn_rate():
    y_true = np.array([1, 1, 1, 0, 0, 0, 1, 0])
    y_pred = np.array([1, 1, 0, 0, 0, 1, 1, 0])  # 1 FN of 4 positives
    m = classification_metrics(y_true, y_pred)
    assert m["false_negative_rate"] == 0.25
    assert "confusion_matrix" in m


def test_rmse():
    m = regression_metrics([0.0, 0.1, 0.2], [0.0, 0.1, 0.25])
    assert m["rmse"] is not None
    assert m["rmse"] < 0.05


def test_thesis_gates():
    m = merge_metric_blocks(
        classification={
            "precision": 0.95,
            "recall": 0.96,
            "f1": 0.95,
            "false_negative_rate": 0.04,
        },
        regression={"rmse": 0.04},
        applicable={
            "recall": True,
            "precision": True,
            "f1": True,
            "fn": True,
            "rmse": True,
            "lead": False,
        },
    )
    assert m["gates"]["meets_thesis"] is True


def test_gates_fail_recall():
    m = apply_thesis_gates(
        {"precision": 0.99, "recall": 0.5, "f1": 0.95, "false_negative_rate": 0.01}
    )
    assert m["gates"]["meets_recall"] is False
    assert m["gates"]["meets_thesis"] is False


def test_horizon_steps():
    assert horizon_steps_from_minutes(1.0, 7.5) == 8
    assert median_delta_minutes(
        pd.Series(pd.date_range("2024-01-01", periods=5, freq="1min", tz="UTC"))
    ) == 1.0


def test_future_targets_columns():
    df = pd.DataFrame(
        {
            "sensor_id": [1] * 30,
            "Leyendo": np.linspace(0, 1, 30),
            "evento_final": [0] * 25 + [1] * 5,
            "Tiempo de Inicio": pd.date_range(
                "2024-01-01", periods=30, freq="1min", tz="UTC"
            ),
        }
    )
    out = add_future_targets(df, horizon_minutes=5, lead_min=5, lead_max=10)
    assert "y_reg" in out.columns
    assert "y_alert_lead" in out.columns
    assert out["y_reg"].notna().sum() > 0


def test_catalog_covers_matrix():
    expected = {
        "decision_tree",
        "random_forest",
        "xgboost",
        "svm",
        "mlp",
        "lstm",
        "gru",
        "transformer",
        "cnn1d",
    }
    assert expected.issubset(set(MODEL_CATALOG))
    assert applicability_for("lstm", "both")["rmse"] is True
    assert applicability_for("svm", "classification")["rmse"] is False
