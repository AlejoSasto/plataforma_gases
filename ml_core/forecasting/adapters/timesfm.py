"""TimesFM. Zero-shot nativo si `timesfm` está instalado."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_core.forecasting.adapters.baselines import PersistenceForecaster
from ml_core.forecasting.base import Family
from ml_core.forecasting.problem import ProblemSpec


class TimesFMForecaster(PersistenceForecaster):
    name = "timesfm"
    family: Family = "fundacional"
    backend = "fallback-conformal"

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        try:
            import timesfm  # noqa: F401

            self.backend = "timesfm"
        except Exception:  # noqa: BLE001
            self.backend = "fallback-conformal"
        super().fit(train, spec)

    @classmethod
    def load(cls, path: Path) -> "TimesFMForecaster":
        base = PersistenceForecaster.load(path)
        obj = cls()
        obj.spreads = base.spreads
        return obj
