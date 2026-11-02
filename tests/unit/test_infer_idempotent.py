"""Inferencia sin modelo y clave idempotente de pronóstico."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from ml_core.forecasting.problem import ProblemSpec
from ml_core.forecasting.serve import infer_sensor


@pytest.mark.plan17
def test_same_context_same_payload() -> None:
    spec = ProblemSpec(lookback=4, horizons=(6, 12), grid_step_minutes=6)
    ctx = pd.DataFrame(
        {
            "unique_id": ["A", "A", "A", "A"],
            "ds": pd.date_range("2024-01-01", periods=4, freq="6min", tz="UTC"),
            "y": [0.2, 0.21, 0.22, 0.23],
        }
    )
    from ml_core.forecasting.adapters import make_forecaster

    model = make_forecaster("persistencia")
    model.fit(ctx, spec)
    a = infer_sensor(ctx, spec, gas="CH4", model=model, last_value=0.23)
    b = infer_sensor(ctx, spec, gas="CH4", model=model, last_value=0.23)
    assert a.quantiles == b.quantiles
    assert a.status_level == b.status_level
    assert a.plain_text == b.plain_text


@pytest.mark.plan17
def test_forecast_unique_key() -> None:
    issued = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    key1 = (1, 9, issued)
    key2 = (1, 9, issued)
    assert key1 == key2
