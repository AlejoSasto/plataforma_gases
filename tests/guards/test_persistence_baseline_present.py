"""Toda evaluación incluye persistencia y calcula MASE."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from ml_core.experiments.run_benchmark import run_benchmark
from ml_core.forecasting.problem import ProblemSpec


@pytest.mark.plan17
def test_persistence_baseline_present() -> None:
    start = datetime(2024, 2, 1, tzinfo=timezone.utc)
    n = 180
    rng = np.random.default_rng(3)
    df = pd.DataFrame(
        {
            "sensor_code": "S1",
            "ts": [start + timedelta(minutes=6 * i) for i in range(n)],
            "value": 0.4 + np.cumsum(rng.normal(0, 0.01, n)),
            "gas": "CH4",
        }
    )
    spec = ProblemSpec(lookback=8, horizons=(6, 12, 18), grid_step_minutes=6)
    rows = run_benchmark(df, spec, models=["ets"])
    names = {r["model"] for r in rows}
    assert "persistencia" in names
    persist = [r for r in rows if r["model"] == "persistencia"]
    assert persist
    assert "mase" in persist[0]
    assert persist[0]["mase"] == persist[0]["mase"]  # no NaN
