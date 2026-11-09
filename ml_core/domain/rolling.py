"""TWA 8 h y STEL 15 min causales. Cobertura menor al 75 % → faltante."""

from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
import pandas as pd


def causal_rolling_mean(
    times: pd.Series | np.ndarray,
    values: pd.Series | np.ndarray,
    *,
    window: timedelta,
    min_coverage: float = 0.75,
    step: timedelta | None = None,
) -> np.ndarray:
    """Media de la ventana (t − window, t]. Solo mira el pasado, incluido t."""
    ts = pd.to_datetime(pd.Series(times), utc=True)
    vals = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    n = len(vals)
    out = np.full(n, np.nan, dtype=float)
    if n == 0:
        return out
    if step is None:
        diffs = ts.diff().dropna()
        if diffs.empty:
            step = window
        else:
            step = diffs.median().to_pytimedelta()
    step_s = max(step.total_seconds(), 1.0)
    expected = max(1, int(math.ceil(window.total_seconds() / step_s)))
    stamps = ts.to_numpy(dtype="datetime64[ns]")
    window_ns = np.timedelta64(int(window.total_seconds() * 1e9), "ns")
    for i in range(n):
        start = stamps[i] - window_ns
        mask = (stamps[: i + 1] > start) & (stamps[: i + 1] <= stamps[i])
        chunk = vals[: i + 1][mask]
        present = chunk[np.isfinite(chunk)]
        if len(present) / expected < min_coverage:
            continue
        out[i] = float(present.mean())
    return out


def attach_twa_stel(
    frame: pd.DataFrame,
    *,
    time_col: str = "ts",
    value_col: str = "value",
    group_cols: tuple[str, ...] = ("sensor_code",),
    step: timedelta | None = None,
) -> pd.DataFrame:
    """Añade twa_8h y stel_15min por grupo. No imputa huecos."""
    out = frame.copy()
    out["twa_8h"] = np.nan
    out["stel_15min"] = np.nan
    if out.empty:
        return out
    for _, idx in out.groupby(list(group_cols), sort=False).groups.items():
        part = out.loc[idx].sort_values(time_col)
        twa = causal_rolling_mean(
            part[time_col],
            part[value_col],
            window=timedelta(hours=8),
            step=step,
        )
        stel = causal_rolling_mean(
            part[time_col],
            part[value_col],
            window=timedelta(minutes=15),
            step=step,
        )
        out.loc[part.index, "twa_8h"] = twa
        out.loc[part.index, "stel_15min"] = stel
    return out
