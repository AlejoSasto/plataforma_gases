from datetime import datetime, timedelta, timezone

import pytest

from ml_core.validation.walk_forward import assert_no_overlap, walk_forward_folds

pytestmark = pytest.mark.plan(15)


def test_walk_forward_no_overlap() -> None:
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [t0 + timedelta(hours=6) for i in range(4 * 30 * 8)]
    folds = walk_forward_folds(ts, lookback=8, k_max=3, min_val_steps=20, block_freq="ME")
    assert folds
    assert folds[-1].is_final_test
    for fold in folds:
        if fold.is_final_test:
            continue
        assert_no_overlap(fold, lookback=8, k_max=3)
        assert set(fold.train_idx).isdisjoint(fold.val_idx)
        assert set(fold.calib_idx).isdisjoint(fold.val_idx)
