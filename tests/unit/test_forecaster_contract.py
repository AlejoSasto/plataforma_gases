"""Contrato de los 10 adaptadores (Plan 17)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pandas as pd
import pytest

from ml_core.forecasting.adapters import ADAPTERS, make_forecaster
from ml_core.forecasting.base import PRED_COLUMNS, ZOO_KEYS, assert_prediction_frame
from ml_core.forecasting.problem import ProblemSpec


def _frame(n: int = 48) -> pd.DataFrame:
    start = datetime(2024, 3, 1, tzinfo=timezone.utc)
    rows = []
    y = 0.4
    for i in range(n):
        y = y + (0.01 if i % 7 else -0.005)
        rows.append(
            {
                "unique_id": "S1",
                "ds": start + timedelta(minutes=6 * i),
                "y": y,
                "gas": "CH4",
                "mask": False,
            }
        )
    return pd.DataFrame(rows)


@pytest.mark.plan17
@pytest.mark.parametrize("key", list(ZOO_KEYS))
def test_adapter_contract(key, tmp_path) -> None:
    assert key in ADAPTERS
    spec = ProblemSpec(lookback=8, horizons=(6, 12, 18), grid_step_minutes=6)
    frame = _frame()
    model = make_forecaster(key)
    assert model.name == key
    assert model.family in {"baseline", "tabular", "recurrente", "transformer", "fundacional"}
    model.fit(frame.iloc[:-6], spec)
    pred = model.predict_quantiles(frame.iloc[:-3], spec)
    assert_prediction_frame(pred)
    for col in PRED_COLUMNS:
        assert col in pred.columns
    assert set(pred["horizon_min"]) <= {6, 12, 18}
    path = tmp_path / key
    model.save(path)
    loaded = type(model).load(path)
    pred2 = loaded.predict_quantiles(frame.iloc[:-3], spec)
    assert_prediction_frame(pred2)
    assert len(pred2) == len(pred)


@pytest.mark.plan17
def test_zoo_has_ten_keys() -> None:
    assert len(ZOO_KEYS) == 10
    assert "persistencia" in ZOO_KEYS
    assert "tft" in ZOO_KEYS
    assert "chronos2" in ZOO_KEYS
