"""Normalización ajustada solo con el bloque de entrenamiento (Plan 20 F3)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TrainOnlyScaler:
    mean_: float = 0.0
    std_: float = 1.0

    def fit(self, train: np.ndarray) -> TrainOnlyScaler:
        arr = np.asarray(train, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            self.mean_, self.std_ = 0.0, 1.0
            return self
        self.mean_ = float(arr.mean())
        std = float(arr.std(ddof=0))
        self.std_ = std if std > 1e-12 else 1.0
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        arr = np.asarray(values, dtype=float)
        return (arr - self.mean_) / self.std_
