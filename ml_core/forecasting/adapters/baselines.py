"""Referencias: persistencia y ETS (Plan 17)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml_core.forecasting.adapters._common import (
    dump_json,
    last_y,
    load_json,
    prediction_rows,
    residual_scale,
    series_by_id,
    train_values,
)
from ml_core.forecasting.base import Family
from ml_core.forecasting.problem import ProblemSpec


class PersistenceForecaster:
    name = "persistencia"
    family: Family = "baseline"
    backend = "native"

    def __init__(self) -> None:
        self.spreads: dict[str, float] = residual_scale(np.array([0.0, 0.1]))

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        del spec
        self.spreads = residual_scale(train_values(train))

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        groups = series_by_id(context)

        def yhat(g: pd.DataFrame, _spec: ProblemSpec) -> float:
            return last_y(g)

        return prediction_rows(groups, spec, yhat, self.spreads)

    def save(self, path: Path) -> None:
        dump_json(path, {"name": self.name, "spreads": self.spreads})

    @classmethod
    def load(cls, path: Path) -> "PersistenceForecaster":
        payload = load_json(path)
        obj = cls()
        obj.spreads = {k: float(v) for k, v in payload["spreads"].items()}
        return obj


class ETSForecaster:
    name = "ets"
    family: Family = "baseline"
    backend = "statsforecast"

    def __init__(self) -> None:
        self.spreads: dict[str, float] = residual_scale(np.array([0.0, 0.1]))
        self.alpha = 0.4
        self.beta = 0.1
        self._ready = False

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        from ml_core.forecasting.errors import ModelUnavailableError

        try:
            import statsforecast  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError("ets", f"falta statsforecast ({type(exc).__name__})") from exc
        del spec
        y = train_values(train)
        self.spreads = residual_scale(y)
        try:
            from statsforecast.models import AutoETS

            del AutoETS
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailableError(
                "ets", f"statsforecast no expone AutoETS ({type(exc).__name__})"
            ) from exc
        raise ModelUnavailableError(
            "ets",
            "el ajuste con statsforecast no está cableado; no se usa otro suavizado con este nombre",
        )

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        from ml_core.forecasting.errors import ModelUnavailableError

        if not self._ready:
            raise ModelUnavailableError(self.name, "ETS no está ajustado con statsforecast")
        groups = series_by_id(context)
        alpha, beta = self.alpha, self.beta

        def yhat(g: pd.DataFrame, _spec: ProblemSpec) -> float:
            y = pd.to_numeric(g["y"], errors="coerce").dropna().to_numpy(dtype=float)
            if y.size == 0:
                return 0.0
            level, trend = float(y[0]), 0.0
            for t in range(1, y.size):
                prev = level
                level = alpha * y[t] + (1 - alpha) * (level + trend)
                trend = beta * (level - prev) + (1 - beta) * trend
            return float(level + trend)

        return prediction_rows(groups, spec, yhat, self.spreads)

    def save(self, path: Path) -> None:
        dump_json(path, {"name": self.name, "spreads": self.spreads, "alpha": self.alpha, "beta": self.beta})

    @classmethod
    def load(cls, path: Path) -> "ETSForecaster":
        payload = load_json(path)
        obj = cls()
        obj.spreads = {k: float(v) for k, v in payload["spreads"].items()}
        obj.alpha = float(payload.get("alpha", 0.4))
        obj.beta = float(payload.get("beta", 0.1))
        obj._ready = True
        return obj


def _fit_holt(y: np.ndarray) -> tuple[float, float]:
    best = (0.4, 0.1, float("inf"))
    for alpha in (0.2, 0.4, 0.6, 0.8):
        for beta in (0.05, 0.1, 0.2):
            level, trend = float(y[0]), 0.0
            err = 0.0
            for t in range(1, y.size):
                pred = level + trend
                err += (y[t] - pred) ** 2
                prev = level
                level = alpha * y[t] + (1 - alpha) * (level + trend)
                trend = beta * (level - prev) + (1 - beta) * trend
            if err < best[2]:
                best = (alpha, beta, err)
    return best[0], best[1]
