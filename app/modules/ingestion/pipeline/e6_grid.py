"""Rejilla regular por sensor. Nunca interpola hacia el futuro (Plan 15 F2 E6)."""

from __future__ import annotations

import pandas as pd

from app.modules.ingestion.pipeline.types import StageResult


def e6_grid(
    df: pd.DataFrame,
    *,
    step_minutes: int,
    max_impute_steps: int = 3,
    value_col: str = "value_canonical",
    time_col: str = "Tiempo de Inicio",
) -> StageResult:
    rows_in = int(len(df))
    if df.empty or step_minutes < 1:
        empty = pd.DataFrame(columns=["sensor_code", "gas", "ts", "value", "is_imputed", "is_missing"])
        return StageResult("E6", empty, rows_in, 0, details={"empty": True})

    freq = f"{int(step_minutes)}min"
    frames: list[pd.DataFrame] = []
    imputed = 0
    missing = 0

    for (sensor, gas), g in df.groupby(["sensor_code", "gas"], sort=False):
        g = g.sort_values(time_col)
        ts = pd.to_datetime(g[time_col], utc=True)
        if ts.empty:
            continue
        start = ts.min().floor(freq)
        end = ts.max()
        grid = pd.date_range(start=start, end=end, freq=freq, tz="UTC")
        series = pd.Series(g[value_col].to_numpy(dtype=float), index=ts)
        series = series[~series.index.duplicated(keep="first")]
        original = series.reindex(grid)
        filled = original.ffill(limit=int(max_impute_steps))
        is_imputed = original.isna() & filled.notna()
        is_missing = filled.isna()
        imputed += int(is_imputed.sum())
        missing += int(is_missing.sum())
        frames.append(
            pd.DataFrame(
                {
                    "sensor_code": sensor,
                    "gas": gas,
                    "ts": grid,
                    "value": filled.to_numpy(),
                    "is_imputed": is_imputed.to_numpy(),
                    "is_missing": is_missing.to_numpy(),
                }
            )
        )

    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return StageResult(
        name="E6",
        dataframe=out,
        rows_in=rows_in,
        rows_out=int(len(out)),
        details={"imputed_steps": imputed, "missing_steps": missing, "step_minutes": step_minutes},
    )
