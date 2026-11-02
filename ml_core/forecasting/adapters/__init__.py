"""Registro de adaptadores del zoo (Plan 17)."""

from __future__ import annotations

from typing import Callable

from ml_core.forecasting.adapters.baselines import ETSForecaster, PersistenceForecaster
from ml_core.forecasting.adapters.chronos import ChronosForecaster
from ml_core.forecasting.adapters.gbm import LightGBMQuantileForecaster
from ml_core.forecasting.adapters.neural import (
    ITransformerForecaster,
    LSTMForecaster,
    PatchTSTForecaster,
    TFTForecaster,
)
from ml_core.forecasting.adapters.timesfm import TimesFMForecaster
from ml_core.forecasting.adapters.ttm import TTMForecaster

ADAPTERS: dict[str, Callable] = {
    "persistencia": PersistenceForecaster,
    "ets": ETSForecaster,
    "lgbm_q": LightGBMQuantileForecaster,
    "lstm": LSTMForecaster,
    "tft": TFTForecaster,
    "patchtst": PatchTSTForecaster,
    "itransformer": ITransformerForecaster,
    "chronos2": ChronosForecaster,
    "timesfm": TimesFMForecaster,
    "ttm": TTMForecaster,
}


def make_forecaster(key: str):
    if key not in ADAPTERS:
        raise KeyError(f"adaptador desconocido: {key}")
    return ADAPTERS[key]()
