"""LightGBM cuantílico (o GradientBoosting de sklearn si no está lightgbm)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml_core.forecasting.adapters._common import (
    dump_json,
    last_y,
    load_json,
    lookback_matrix,
    prediction_rows,
    residual_scale,
    series_by_id,
    train_values,
)
from ml_core.forecasting.base import Family
from ml_core.forecasting.dataset import horizon_steps
from ml_core.forecasting.problem import ProblemSpec


def _make_regressor(alpha: float):
    try:
        import lightgbm as lgb

        return lgb.LGBMRegressor(
            objective="quantile",
            alpha=alpha,
            n_estimators=40,
            min_child_samples=4,
            verbosity=-1,
        ), "lightgbm"
    except Exception:  # noqa: BLE001
        from sklearn.ensemble import GradientBoostingRegressor

        return GradientBoostingRegressor(
            loss="quantile",
            alpha=alpha,
            n_estimators=40,
            max_depth=2,
            random_state=17,
        ), "sklearn-gbr"


class LightGBMQuantileForecaster:
    name = "lgbm_q"
    family: Family = "tabular"
    backend = "sklearn-gbr"

    def __init__(self) -> None:
        self.spreads: dict[str, float] = residual_scale(np.array([0.0, 0.1]))
        self.lookback = 8
        self.model_q50 = None
        self.k_step = 1

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        y = train_values(train)
        self.spreads = residual_scale(y)
        self.lookback = min(int(spec.lookback), max(4, y.size // 3), 24)
        steps = horizon_steps(spec)
        self.k_step = int(steps[0]) if steps else 1
        X, yt = lookback_matrix(y, self.lookback, self.k_step)
        if len(X) < 8:
            self.model_q50 = None
            return
        model, backend = _make_regressor(0.5)
        self.backend = backend
        model.fit(X, yt)
        self.model_q50 = model

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        groups = series_by_id(context)
        lookback = self.lookback
        model = self.model_q50

        def yhat(g: pd.DataFrame, _spec: ProblemSpec) -> float:
            arr = pd.to_numeric(g["y"], errors="coerce").dropna().to_numpy(dtype=float)
            if model is None or arr.size < lookback:
                return last_y(g)
            x = arr[-lookback:].reshape(1, -1)
            return float(model.predict(x)[0])

        return prediction_rows(groups, spec, yhat, self.spreads)

    def save(self, path: Path) -> None:
        import pickle

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        dump_json(
            path.with_suffix(".json"),
            {"name": self.name, "spreads": self.spreads, "lookback": self.lookback, "k_step": self.k_step},
        )
        with path.open("wb") as fh:
            pickle.dump(self.model_q50, fh)

    @classmethod
    def load(cls, path: Path) -> "LightGBMQuantileForecaster":
        import pickle

        path = Path(path)
        obj = cls()
        meta = load_json(path.with_suffix(".json"))
        obj.spreads = {k: float(v) for k, v in meta["spreads"].items()}
        obj.lookback = int(meta["lookback"])
        obj.k_step = int(meta.get("k_step", 1))
        with path.open("rb") as fh:
            obj.model_q50 = pickle.load(fh)
        return obj
