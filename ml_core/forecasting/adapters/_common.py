"""Utilidades compartidas de los adaptadores."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml_core.forecasting.dataset import horizon_steps, to_long
from ml_core.forecasting.problem import ProblemSpec

TAU_MAP = ((0.10, "q10"), (0.50, "q50"), (0.90, "q90"), (0.95, "q95"))


def series_by_id(train: pd.DataFrame) -> dict[str, pd.DataFrame]:
    long = to_long(train) if "y" not in train.columns else train.copy()
    long["ds"] = pd.to_datetime(long["ds"], utc=True)
    return {str(uid): g.sort_values("ds") for uid, g in long.groupby("unique_id", sort=False)}


def last_y(frame: pd.DataFrame) -> float:
    y = pd.to_numeric(frame["y"], errors="coerce").dropna()
    return float(y.iloc[-1]) if len(y) else 0.0


def residual_scale(y: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    if y.size < 4:
        sigma = 0.05
    else:
        d = np.diff(y)
        sigma = float(np.median(np.abs(d - np.median(d))) * 1.4826 + 1e-6)
    z = {0.10: -1.2816, 0.50: 0.0, 0.90: 1.2816, 0.95: 1.6449}
    return {name: float(z[tau] * sigma) for tau, name in TAU_MAP}


def point_to_quantiles(yhat: float, spreads: dict[str, float]) -> dict[str, float]:
    q50 = float(yhat)
    q10 = q50 + float(spreads.get("q10", -0.05))
    q90 = q50 + float(spreads.get("q90", 0.05))
    q95 = q50 + float(spreads.get("q95", 0.08))
    q10 = min(q10, q50)
    q90 = max(q90, q50)
    q95 = max(q95, q90)
    return {"q10": q10, "q50": q50, "q90": q90, "q95": q95}


def prediction_rows(
    groups: dict[str, pd.DataFrame],
    spec: ProblemSpec,
    yhat_fn,
    spreads: dict[str, float],
) -> pd.DataFrame:
    rows: list[dict] = []
    for uid, g in groups.items():
        issued = pd.to_datetime(g["ds"].iloc[-1], utc=True)
        yhat = float(yhat_fn(g, spec))
        q = point_to_quantiles(yhat, spreads)
        for h in spec.horizons:
            rows.append({"unique_id": uid, "issued_at": issued, "horizon_min": int(h), **q})
    return pd.DataFrame(rows)


def dump_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def train_values(train: pd.DataFrame) -> np.ndarray:
    long = to_long(train) if "y" not in train.columns else train
    return pd.to_numeric(long["y"], errors="coerce").dropna().to_numpy(dtype=float)


def lookback_matrix(y: np.ndarray, lookback: int, horizon_step: int) -> tuple[np.ndarray, np.ndarray]:
    """X[t-lookback:t] → y[t+h-1]. Solo pasado."""
    y = np.asarray(y, dtype=float)
    n = y.size
    xs, ys = [], []
    last = n - horizon_step
    for t in range(lookback, last):
        xs.append(y[t - lookback : t])
        ys.append(y[t + horizon_step - 1])
    if not xs:
        return np.zeros((0, lookback)), np.zeros((0,))
    return np.vstack(xs), np.asarray(ys, dtype=float)


# re-export for adapters that need steps
__all__ = [
    "TAU_MAP",
    "series_by_id",
    "last_y",
    "residual_scale",
    "point_to_quantiles",
    "prediction_rows",
    "dump_json",
    "load_json",
    "train_values",
    "lookback_matrix",
    "horizon_steps",
]
