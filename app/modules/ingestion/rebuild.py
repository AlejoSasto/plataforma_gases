"""Reconstrucción reproducible de rejilla y episodios (Plan 16)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.ingestion.pipeline.e6_grid import e6_grid
from ml_core.domain.events import extract_event_spans
from ml_core.domain.thresholds import THRESHOLD_SEED, ThresholdSpec


def rebuild_grid_frame(
    df: pd.DataFrame,
    *,
    step_minutes: int = 6,
    max_impute_steps: int = 3,
) -> pd.DataFrame:
    result = e6_grid(df, step_minutes=step_minutes, max_impute_steps=max_impute_steps)
    out = result.dataframe.copy()
    return out.sort_values(["sensor_code", "gas", "ts"]).reset_index(drop=True)


def rebuild_events_frame(
    grid: pd.DataFrame,
    specs: list[ThresholdSpec] | None = None,
) -> pd.DataFrame:
    used = specs or list(THRESHOLD_SEED)
    rows: list[dict[str, Any]] = []
    for spec in used:
        rows.extend(extract_event_spans(grid, spec))
    if not rows:
        return pd.DataFrame(
            columns=[
                "sensor_code",
                "gas_code",
                "level",
                "started_at",
                "ended_at",
                "peak_value",
                "peak_at",
            ]
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["sensor_code", "gas_code", "level", "started_at"]).reset_index(drop=True)


def frame_signature(df: pd.DataFrame) -> tuple[int, str]:
    payload = df.to_json(orient="split", date_format="iso") if not df.empty else "[]"
    return len(df), payload
