"""Los estadísticos de normalización salen solo del train (Plan 20 F3)."""

from __future__ import annotations

import numpy as np
import pytest

from ml_core.validation.scaling import TrainOnlyScaler

pytestmark = pytest.mark.plan(15)


def test_scalers_fit_on_train_only() -> None:
    rng = np.random.default_rng(3)
    train = rng.normal(2.0, 0.5, 200)
    rest = rng.normal(8.0, 0.5, 200)
    full = np.concatenate([train, rest])
    scaler = TrainOnlyScaler().fit(train)
    assert abs(scaler.mean_ - float(train.mean())) < 1e-9
    assert abs(scaler.std_ - float(train.std(ddof=0))) < 1e-9
    assert abs(scaler.mean_ - float(full.mean())) > 0.5
