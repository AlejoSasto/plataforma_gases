"""Rejilla → formato largo causal (unique_id, ds, y, máscara)."""

from __future__ import annotations

import pandas as pd

from ml_core.forecasting.problem import ProblemSpec

LONG_COLUMNS = ("unique_id", "ds", "y")


def to_long(
    df: pd.DataFrame,
    *,
    id_col: str = "sensor_code",
    time_col: str = "ts",
    y_col: str = "value",
    gas_col: str | None = "gas",
    mask_col: str | None = "is_missing",
) -> pd.DataFrame:
    """Convierte una rejilla o lecturas a formato largo. No imputa el futuro."""
    if df.empty:
        return pd.DataFrame(columns=[*LONG_COLUMNS, "gas", "mask"])
    work = df.copy()
    if id_col not in work.columns and "unique_id" in work.columns:
        id_col = "unique_id"
    if time_col not in work.columns:
        for cand in ("Tiempo de Inicio", "tiempo_inicio", "ds"):
            if cand in work.columns:
                time_col = cand
                break
    if y_col not in work.columns:
        for cand in ("value_canonical", "Leyendo", "leyendo", "y"):
            if cand in work.columns:
                y_col = cand
                break
    out = pd.DataFrame(
        {
            "unique_id": work[id_col].astype(str),
            "ds": pd.to_datetime(work[time_col], utc=True),
            "y": pd.to_numeric(work[y_col], errors="coerce"),
        }
    )
    if gas_col and gas_col in work.columns:
        out["gas"] = work[gas_col].astype(str)
    elif "Tipo de Gas" in work.columns:
        out["gas"] = work["Tipo de Gas"].astype(str)
    else:
        out["gas"] = "UNKNOWN"
    if mask_col and mask_col in work.columns:
        out["mask"] = work[mask_col].astype(bool)
    else:
        out["mask"] = out["y"].isna()
    out = out.sort_values(["unique_id", "ds"]).reset_index(drop=True)
    return out


def horizon_steps(spec: ProblemSpec) -> tuple[int, ...]:
    step = max(1, int(spec.grid_step_minutes))
    steps = []
    for h in spec.horizons:
        k = int(round(int(h) / step))
        steps.append(max(1, k))
    return tuple(steps)


def last_context(frame: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
    """Últimos `lookback` puntos por serie, sin mirar más allá del máximo ds."""
    if frame.empty:
        return frame
    parts = []
    for uid, g in frame.groupby("unique_id", sort=False):
        g = g.sort_values("ds")
        parts.append(g.tail(int(spec.lookback)))
        del uid
    return pd.concat(parts, ignore_index=True)
