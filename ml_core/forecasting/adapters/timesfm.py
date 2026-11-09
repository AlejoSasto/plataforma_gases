"""TimesFM. Si la librería no está, falla. No usa la persistencia con otro nombre."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_core.forecasting.base import Family
from ml_core.forecasting.errors import ModelUnavailableError
from ml_core.forecasting.problem import ProblemSpec


class TimesFMForecaster:
    name = "timesfm"
    family: Family = "fundacional"
    backend = "timesfm"

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        del train, spec
        try:
            import timesfm  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(self.name, f"falta timesfm ({type(exc).__name__})") from exc
        raise ModelUnavailableError(self.name, "no hay pesos locales de TimesFM; no se sustituye el modelo")

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        del context, spec
        raise ModelUnavailableError(self.name, "TimesFM no está cargado")

    def save(self, path: Path) -> None:
        del path
        raise ModelUnavailableError(self.name, "no hay artefacto que guardar")

    @classmethod
    def load(cls, path: Path) -> "TimesFMForecaster":
        del path
        raise ModelUnavailableError(cls.name, "no hay artefacto de TimesFM")
