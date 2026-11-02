"""La prueba final es un único bloque intocable (Plan 20 F3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ml_core.validation.walk_forward import walk_forward_folds

pytestmark = pytest.mark.plan(15)


def test_final_test_untouched() -> None:
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts = [t0 + timedelta(hours=6 * i) for i in range(4 * 30 * 8)]
    folds = walk_forward_folds(ts, lookback=8, k_max=3, min_val_steps=20)
    finals = [f for f in folds if f.is_final_test]
    assert len(finals) == 1
    final = finals[0]
    assert final.train_idx == ()
    assert final.calib_idx == ()
    cv_used: set[int] = set()
    for fold in folds:
        if fold.is_final_test:
            continue
        cv_used.update(fold.train_idx)
        cv_used.update(fold.calib_idx)
        cv_used.update(fold.val_idx)
    assert set(final.val_idx).isdisjoint(cv_used)
