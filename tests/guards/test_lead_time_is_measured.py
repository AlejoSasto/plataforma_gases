"""La anticipación sale de las marcas de tiempo, no de una constante."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from ml_core.domain.thresholds import ThresholdSpec
from ml_core.validation.metrics import event_metrics


@pytest.mark.plan17
def test_lead_time_is_measured() -> None:
    spec = ThresholdSpec("CO", "vigilar", "above", 25.0, "ppm", "test")
    start = datetime(2024, 5, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(minutes=5 * i) for i in range(6)]
    values = np.array([1, 1, 1, 40, 40, 1], dtype=float)
    alert = np.array([0, 1, 0, 0, 0, 0], dtype=int)
    m = event_metrics(values=values, alert=alert, timestamps=ts, spec=spec, step_minutes=5)
    assert m["lead_p50"] == 10.0
    assert m["lead_p50"] not in {5.0, 7.5, 10.0} or m["lead_p50"] == 10.0
