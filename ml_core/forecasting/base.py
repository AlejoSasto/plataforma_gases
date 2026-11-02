"""Interfaz única de pronóstico cuantílico (Plan 17)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

import pandas as pd

from ml_core.forecasting.problem import ProblemSpec

Family = Literal["baseline", "tabular", "recurrente", "transformer", "fundacional"]

PRED_COLUMNS: tuple[str, ...] = (
    "unique_id",
    "issued_at",
    "horizon_min",
    "q10",
    "q50",
    "q90",
    "q95",
)

ZOO_KEYS: tuple[str, ...] = (
    "persistencia",
    "ets",
    "lgbm_q",
    "lstm",
    "tft",
    "patchtst",
    "itransformer",
    "chronos2",
    "timesfm",
    "ttm",
)


@runtime_checkable
class Forecaster(Protocol):
    name: str
    family: Family
    backend: str

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None: ...

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        """Devuelve unique_id, issued_at, horizon_min, q10, q50, q90, q95."""

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> "Forecaster": ...


def assert_prediction_frame(df: pd.DataFrame) -> None:
    missing = [c for c in PRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"faltan columnas {missing}")
    if df.empty:
        return
    if (df["q10"] > df["q50"] + 1e-9).any() or (df["q50"] > df["q90"] + 1e-9).any():
        raise ValueError("cuantiles no ordenados q10 ≤ q50 ≤ q90")
