"""Tiny Time Mixer. Sin la librería del modelo, falla. No entrena otra red con este nombre."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_core.forecasting.base import Family
from ml_core.forecasting.errors import ModelUnavailableError
from ml_core.forecasting.problem import ProblemSpec


class TTMForecaster:
    name = "ttm"
    family: Family = "fundacional"
    backend = "granite-tsfm"

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        del train, spec
        try:
            import granite_tsfm  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(self.name, f"falta granite-tsfm ({type(exc).__name__})") from exc
        raise ModelUnavailableError(self.name, "no hay pesos locales de TTM; no se sustituye el modelo")

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        del context, spec
        raise ModelUnavailableError(self.name, "TTM no está cargado")

    def save(self, path: Path) -> None:
        del path
        raise ModelUnavailableError(self.name, "no hay artefacto que guardar")

    @classmethod
    def load(cls, path: Path) -> "TTMForecaster":
        del path
        raise ModelUnavailableError(cls.name, "no hay artefacto de TTM")
