"""Ramas de validación que el jurado puede preguntar (Plan 20 cobertura)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from ml_core.domain.thresholds import ThresholdSpec
from ml_core.validation.metrics import (
    bootstrap_ci,
    event_metrics,
    interval_coverage,
    mase,
    pinball_mean,
)
from ml_core.validation.scaling import TrainOnlyScaler
from ml_core.validation.walk_forward import Fold, assert_no_overlap, walk_forward_folds

pytestmark = pytest.mark.plan20


def test_mase_and_pinball_empty() -> None:
    y = np.array([1.0, 1.0])
    assert np.isnan(mase(y, y, y))
    assert np.isnan(pinball_mean(np.array([]), np.array([]), 0.5))
    assert np.isnan(interval_coverage(np.array([]), np.array([]), np.array([])))


def test_bootstrap_ci_too_short_and_ok() -> None:
    short = bootstrap_ci([1.0, 2.0])
    assert short["low"] is None and short["high"] is None
    ok = bootstrap_ci([1.0, 2.0, 3.0, 4.0], n_boot=20)
    assert ok["low"] is not None and ok["high"] is not None
    assert ok["low"] <= ok["high"]


def test_event_metrics_claimed_and_negative_lead() -> None:
    spec = ThresholdSpec("CH4", "actuar", "above", 5.0, "%vol", "test")
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [start + timedelta(minutes=i) for i in range(6)]
    values = np.array([0, 9, 0, 9, 0, 0], dtype=float)
    alert = np.array([1, 0, 0, 0, 0, 0], dtype=int)
    m = event_metrics(values=values, alert=alert, timestamps=ts, spec=spec, step_minutes=1)
    assert m["n_events"] == 2
    assert m["tp"] == 1
    backward = list(reversed(ts))
    event_metrics(values=values, alert=alert, timestamps=backward, spec=spec, step_minutes=1)


def test_scaler_empty_and_transform() -> None:
    scaler = TrainOnlyScaler().fit(np.array([np.nan, np.inf]))
    assert scaler.mean_ == 0.0 and scaler.std_ == 1.0
    out = TrainOnlyScaler(mean_=2.0, std_=2.0).transform(np.array([4.0, 6.0]))
    assert list(out) == [1.0, 2.0]


def test_walk_forward_short_and_as_dict() -> None:
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert walk_forward_folds([t0, t0 + timedelta(hours=1)], lookback=8, k_max=3) == []
    fold = Fold("x", (0, 1), (2,), (10, 11), False)
    assert fold.as_dict()["name"] == "x"
    assert_no_overlap(Fold("final-test", tuple(), tuple(), (1,), True), lookback=1, k_max=1)
    assert_no_overlap(Fold("empty", tuple(), tuple(), tuple(), False), lookback=1, k_max=1)
    with pytest.raises(AssertionError):
        assert_no_overlap(Fold("overlap", (0, 1, 2), tuple(), (2, 3), False), lookback=1, k_max=1)
    with pytest.raises(AssertionError):
        assert_no_overlap(Fold("gap", (0, 1), tuple(), (2, 3), False), lookback=4, k_max=4)
