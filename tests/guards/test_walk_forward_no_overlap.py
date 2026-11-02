from datetime import datetime, timedelta, timezone

import pytest

from ml_core.validation.walk_forward import assert_no_overlap, walk_forward_folds

pytestmark = pytest.mark.plan(15)


def test_walk_forward_no_overlap() -> None:
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [t0 + timedelta(hours=i) for i in range(24 * 200)]
    folds = walk_forward_folds(ts, lookback=24, k_max=3, min_val_steps=20, block_freq="ME")
    cv = [f for f in folds if not f.is_final_test]
    assert cv
    for fold in cv:
        assert_no_overlap(fold, lookback=24, k_max=3)
