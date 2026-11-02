"""Métricas unificadas y gates thesis."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    mean_squared_error,
    precision_score,
    recall_score,
)

from app.core.config import settings


def classification_metrics(y_true, y_pred) -> dict[str, Any]:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(x) for x in cm.ravel()) if cm.size == 4 else (0, 0, 0, 0)
    support_pos = int((y_true == 1).sum())
    fn_rate = float(fn / support_pos) if support_pos > 0 else 0.0
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_negative_rate": fn_rate,
        "support_pos": support_pos,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def regression_metrics(y_true, y_pred) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not mask.any():
        return {"rmse": None, "mae": None}
    yt, yp = y_true[mask], y_pred[mask]
    rmse = float(np.sqrt(mean_squared_error(yt, yp)))
    mae = float(np.mean(np.abs(yt - yp)))
    return {"rmse": rmse, "mae": mae}


def lead_time_metrics(
    y_lead_true,
    y_alert_pred,
    *,
    lead_min: float | None = None,
    lead_max: float | None = None,
) -> dict[str, Any]:
    """
    Aproxima hit-rate de alerta anticipada: proporción de ventanas con evento
    futuro (y_lead_true=1) donde el modelo alertó (y_alert_pred=1).
    lead_time_minutes_mean se reporta como punto medio del rango configurado
    cuando hay hits (proxy operativo documentado).
    """
    yt = np.asarray(y_lead_true).astype(int)
    yp = np.asarray(y_alert_pred).astype(int)
    lo = float(lead_min if lead_min is not None else settings.ml_lead_minutes_min)
    hi = float(lead_max if lead_max is not None else settings.ml_lead_minutes_max)
    mid = (lo + hi) / 2.0
    pos = yt == 1
    if not pos.any():
        return {
            "lead_time_minutes_mean": None,
            "lead_time_hit_rate": None,
            "lead_window_min": lo,
            "lead_window_max": hi,
        }
    hits = (yp[pos] == 1).sum()
    rate = float(hits / pos.sum())
    return {
        "lead_time_minutes_mean": mid if hits > 0 else None,
        "lead_time_hit_rate": rate,
        "lead_window_min": lo,
        "lead_window_max": hi,
    }


def apply_thesis_gates(
    metrics: dict[str, Any],
    *,
    applicable: Optional[dict[str, bool]] = None,
) -> dict[str, Any]:
    """Añade flags meets_* según umbrales y aplicabilidad del algoritmo."""
    app = applicable or {
        "recall": True,
        "precision": True,
        "f1": True,
        "fn": True,
        "rmse": "rmse" in metrics and metrics.get("rmse") is not None,
        "lead": metrics.get("lead_time_hit_rate") is not None,
    }
    out = dict(metrics)
    recall = metrics.get("recall")
    precision = metrics.get("precision")
    f1 = metrics.get("f1")
    fn = metrics.get("false_negative_rate")
    rmse = metrics.get("rmse")
    lead_rate = metrics.get("lead_time_hit_rate")

    meets_recall = (
        bool(recall is not None and recall >= settings.thesis_recall_min)
        if app.get("recall")
        else None
    )
    meets_precision = (
        bool(precision is not None and precision >= settings.thesis_precision_min)
        if app.get("precision")
        else None
    )
    meets_f1 = (
        bool(f1 is not None and f1 >= settings.thesis_f1_min) if app.get("f1") else None
    )
    meets_fn = (
        bool(fn is not None and fn <= settings.thesis_fn_max) if app.get("fn") else None
    )
    meets_rmse = (
        bool(rmse is not None and rmse <= settings.thesis_rmse_max)
        if app.get("rmse")
        else None
    )
    # Lead: hit rate ≥ 0.5 y mean dentro de ventana (proxy)
    meets_lead = None
    if app.get("lead") and lead_rate is not None:
        mean = metrics.get("lead_time_minutes_mean")
        in_window = mean is None or (
            settings.ml_lead_minutes_min <= mean <= settings.ml_lead_minutes_max
        )
        meets_lead = bool(lead_rate >= 0.5 and in_window)

    gates = {
        "meets_recall": meets_recall,
        "meets_precision": meets_precision,
        "meets_f1": meets_f1,
        "meets_fn": meets_fn,
        "meets_rmse": meets_rmse,
        "meets_lead": meets_lead,
    }
    evaluated = [v for v in gates.values() if v is not None]
    gates["meets_thesis"] = all(evaluated) if evaluated else False
    out["gates"] = gates
    out["thresholds"] = {
        "recall_min": settings.thesis_recall_min,
        "precision_min": settings.thesis_precision_min,
        "f1_min": settings.thesis_f1_min,
        "fn_max": settings.thesis_fn_max,
        "rmse_max": settings.thesis_rmse_max,
        "lead_min": settings.ml_lead_minutes_min,
        "lead_max": settings.ml_lead_minutes_max,
    }
    return out


def merge_metric_blocks(
    *,
    classification: Optional[dict[str, Any]] = None,
    regression: Optional[dict[str, Any]] = None,
    temporal: Optional[dict[str, Any]] = None,
    applicable: Optional[dict[str, bool]] = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if classification:
        merged.update(classification)
    if regression:
        merged.update(regression)
    if temporal:
        merged.update(temporal)
    return apply_thesis_gates(merged, applicable=applicable)
