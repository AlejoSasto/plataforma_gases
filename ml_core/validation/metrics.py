"""Métricas de pronóstico, eventos y operación (Plan 17 §7)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pandas as pd

from ml_core.domain.events import onset_mask
from ml_core.domain.thresholds import ThresholdSpec
from ml_core.forecasting.problem import pinball_loss


def mae(y: np.ndarray, yhat: np.ndarray) -> float:
    yt, yp = _pair(y, yhat)
    return float(np.mean(np.abs(yt - yp))) if yt.size else float("nan")


def rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    yt, yp = _pair(y, yhat)
    return float(np.sqrt(np.mean((yt - yp) ** 2))) if yt.size else float("nan")


def mase(y: np.ndarray, yhat: np.ndarray, y_persist: np.ndarray) -> float:
    err = mae(y, yhat)
    den = mae(y, y_persist)
    if not np.isfinite(den) or den < 1e-12:
        return float("nan")
    return float(err / den)


def pinball_mean(y: np.ndarray, q_hat: np.ndarray, tau: float) -> float:
    yt, qh = _pair(y, q_hat)
    if yt.size == 0:
        return float("nan")
    return float(np.mean([pinball_loss(float(a), float(b), tau) for a, b in zip(yt, qh)]))


def interval_coverage(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    yt, l = _pair(y, lo)
    _, h = _pair(y, hi)
    n = min(yt.size, l.size, h.size)
    if n == 0:
        return float("nan")
    return float(((yt[:n] >= l[:n]) & (yt[:n] <= h[:n])).mean())


def interval_width(lo: np.ndarray, hi: np.ndarray) -> float:
    a, b = _pair(lo, hi)
    return float(np.mean(b - a)) if a.size else float("nan")


def forecast_metrics(
    y: np.ndarray,
    q10: np.ndarray,
    q50: np.ndarray,
    q90: np.ndarray,
    y_persist: np.ndarray,
) -> dict[str, float]:
    return {
        "mae": mae(y, q50),
        "rmse": rmse(y, q50),
        "mase": mase(y, q50, y_persist),
        "pinball": float(
            np.nanmean(
                [
                    pinball_mean(y, q10, 0.10),
                    pinball_mean(y, q50, 0.50),
                    pinball_mean(y, q90, 0.90),
                ]
            )
        ),
        "coverage_10_90": interval_coverage(y, q10, q90),
        "width_10_90": interval_width(q10, q90),
    }


def event_metrics(
    *,
    values: np.ndarray,
    alert: np.ndarray,
    timestamps: Sequence,
    spec: ThresholdSpec,
    step_minutes: float,
    shift_hours: float = 8.0,
) -> dict[str, Any]:
    """Verdaderos positivos = inicios avisados a tiempo. Anticipación por episodio."""
    onsets = onset_mask(np.asarray(values, dtype=float), spec)
    alert_b = np.asarray(alert, dtype=bool)
    ts = pd.to_datetime(list(timestamps), utc=True)
    n_events = int(onsets.sum())
    hits = 0
    leads: list[float] = []
    onset_idx = np.where(onsets)[0]
    claimed: set[int] = set()
    for t in onset_idx:
        window = np.where(alert_b[: t + 1])[0]
        if window.size == 0:
            continue
        first = int(window[0])
        if first in claimed:
            continue
        lead = (ts[t] - ts[first]).total_seconds() / 60.0
        if lead < 0:
            continue
        hits += 1
        leads.append(float(lead))
        claimed.add(first)
    n_alerts = int(alert_b.sum())
    tp = hits
    fp = max(0, n_alerts - tp)
    fn = max(0, n_events - tp)
    recall = (tp / n_events) if n_events else 0.0
    precision = (tp / n_alerts) if n_alerts else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    n_steps = max(len(values), 1)
    steps_per_shift = max((shift_hours * 60.0) / max(step_minutes, 1.0), 1.0)
    n_shifts = max(n_steps / steps_per_shift, 1e-6)
    p10 = float(np.quantile(leads, 0.10)) if leads else None
    p50 = float(np.quantile(leads, 0.50)) if leads else None
    return {
        "n_events": n_events,
        "n_alerts": n_alerts,
        "recall": float(recall),
        "precision": float(precision),
        "f1": float(f1),
        "fn_rate": float(1.0 - recall) if n_events else None,
        "lead_p10": p10,
        "lead_p50": p50,
        "fa_per_shift": float(fp / n_shifts),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def bootstrap_ci(values: list[float], *, n_boot: int = 400, alpha: float = 0.05) -> dict[str, float | None]:
    if len(values) < 3:
        return {"low": None, "high": None}
    rng = np.random.default_rng(17)
    arr = np.asarray(values, dtype=float)
    samples = [float(np.mean(rng.choice(arr, size=arr.size, replace=True))) for _ in range(n_boot)]
    lo, hi = np.quantile(samples, [alpha / 2, 1 - alpha / 2])
    return {"low": float(lo), "high": float(hi)}


def _pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    n = min(x.size, y.size)
    x, y = x[:n], y[:n]
    m = np.isfinite(x) & np.isfinite(y)
    return x[m], y[m]
