"""Métricas por evento con casos a mano (Plan 17)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from ml_core.domain.thresholds import ThresholdSpec
from ml_core.validation.metrics import event_metrics


@pytest.mark.plan17
def test_event_metrics_hand_case() -> None:
    spec = ThresholdSpec("CH4", "actuar", "above", 5.0, "%vol", "test")
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(minutes=i) for i in range(8)]
    values = np.array([0, 0, 0, 9, 9, 0, 0, 0], dtype=float)
    # aviso en t=1, inicio real en t=3 → anticipación 2 min
    alert = np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=int)
    m = event_metrics(
        values=values,
        alert=alert,
        timestamps=ts,
        spec=spec,
        step_minutes=1,
        shift_hours=8,
    )
    assert m["n_events"] == 1
    assert m["recall"] == 1.0
    assert m["lead_p50"] == 2.0
    assert m["lead_p10"] == 2.0


@pytest.mark.plan17
def test_missed_event_is_false_negative() -> None:
    spec = ThresholdSpec("CH4", "actuar", "above", 5.0, "%vol", "test")
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(minutes=i) for i in range(4)]
    values = np.array([0, 0, 9, 0], dtype=float)
    alert = np.zeros(4, dtype=int)
    m = event_metrics(values=values, alert=alert, timestamps=ts, spec=spec, step_minutes=1)
    assert m["n_events"] == 1
    assert m["recall"] == 0.0
    assert m["fn_rate"] == 1.0
    assert m["lead_p50"] is None
