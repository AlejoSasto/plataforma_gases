"""rebuild_grid y rebuild_events reproducen los mismos conteos (Plan 16)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pandas as pd
import pytest

from app.modules.ingestion.rebuild import frame_signature, rebuild_events_frame, rebuild_grid_frame
from ml_core.domain.thresholds import THRESHOLD_SEED


def _sample_frame() -> pd.DataFrame:
    start = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    rows = []
    for i in range(20):
        ts = start + timedelta(minutes=6 * i)
        ch4 = 0.2 if i < 8 or i > 12 else 1.8
        rows.append(
            {
                "sensor_code": "S1",
                "gas": "CH4",
                "Tiempo de Inicio": ts,
                "value_canonical": ch4,
            }
        )
        o2 = 20.8 if i < 5 or i > 10 else 16.5
        rows.append(
            {
                "sensor_code": "S2",
                "gas": "O2",
                "Tiempo de Inicio": ts,
                "value_canonical": o2,
            }
        )
    return pd.DataFrame(rows)


@pytest.mark.plan16
def test_rebuild_grid_same_counts_twice() -> None:
    df = _sample_frame()
    a = rebuild_grid_frame(df, step_minutes=6)
    b = rebuild_grid_frame(df, step_minutes=6)
    assert frame_signature(a) == frame_signature(b)
    assert len(a) > 0
    assert set(a.columns) >= {"sensor_code", "gas", "ts", "value", "is_imputed", "is_missing"}


@pytest.mark.plan16
def test_rebuild_events_same_counts_twice() -> None:
    grid = rebuild_grid_frame(_sample_frame(), step_minutes=6)
    a = rebuild_events_frame(grid, list(THRESHOLD_SEED))
    b = rebuild_events_frame(grid, list(THRESHOLD_SEED))
    assert frame_signature(a) == frame_signature(b)
    assert (a["gas_code"] == "CH4").any()
    assert (a["level"] == "evacuar").any()
