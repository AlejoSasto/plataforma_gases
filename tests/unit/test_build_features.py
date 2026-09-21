"""Tests unitarios de feature engineering."""

from __future__ import annotations

from app.core.database import SessionLocal
from ml_core.features.build_features import FEATURE_COLUMNS, LABEL_COLUMN, build_features


def test_build_features_from_db() -> None:
    db = SessionLocal()
    try:
        split = build_features(db, max_rows=8000, test_months=3)
        assert split.n_total > 0
        assert split.n_positive > 0
        assert not split.train.empty
        assert not split.test.empty
        for col in FEATURE_COLUMNS + [LABEL_COLUMN]:
            assert col in split.train.columns
            assert col in split.test.columns
    finally:
        db.close()
