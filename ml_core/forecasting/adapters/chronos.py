"""Chronos. Si la librería o los pesos no están, falla. No hereda la persistencia."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_core.forecasting.base import Family
from ml_core.forecasting.errors import ModelUnavailableError
from ml_core.forecasting.problem import ProblemSpec


class ChronosForecaster:
    name = "chronos2"
    family: Family = "fundacional"
    backend = "chronos-forecasting"

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        del train, spec
        try:
            import chronos  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(self.name, f"falta chronos-forecasting ({type(exc).__name__})") from exc
        raise ModelUnavailableError(self.name, "no hay pesos locales de Chronos; no se sustituye el modelo")

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        del context, spec
        raise ModelUnavailableError(self.name, "Chronos no está cargado")

    def save(self, path: Path) -> None:
        del path
        raise ModelUnavailableError(self.name, "no hay artefacto que guardar")

    @classmethod
    def load(cls, path: Path) -> "ChronosForecaster":
        del path
        raise ModelUnavailableError(cls.name, "no hay artefacto de Chronos")


class ChronosBoltForecaster(ChronosForecaster):
    name = "chronos"
