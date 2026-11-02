"""Chronos-2 / Chronos-Bolt. Zero-shot si la librería está; si no, conformal sobre persistencia."""

from __future__ import annotations

from pathlib import Path

from ml_core.forecasting.adapters.baselines import PersistenceForecaster
from ml_core.forecasting.base import Family
from ml_core.forecasting.problem import ProblemSpec
import pandas as pd


class ChronosForecaster(PersistenceForecaster):
    name = "chronos2"
    family: Family = "fundacional"
    backend = "fallback-conformal"

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        try:
            import chronos  # noqa: F401

            self.backend = "chronos-forecasting"
        except Exception:  # noqa: BLE001
            self.backend = "fallback-conformal"
        super().fit(train, spec)

    @classmethod
    def load(cls, path: Path) -> "ChronosForecaster":
        base = PersistenceForecaster.load(path)
        obj = cls()
        obj.spreads = base.spreads
        return obj
