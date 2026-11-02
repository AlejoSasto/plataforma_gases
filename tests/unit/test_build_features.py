"""Tests unitarios de feature engineering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ml_core.features.build_features import FEATURE_COLUMNS, LABEL_COLUMN, build_features
from tests.factories import readings_series, sensor, site


def test_build_features_from_db(db: Session) -> None:
    zona = site(db, name="Zona features")
    sen = sensor(db, code="FEAT#CH4", gas_type="CH4", site_row=zona)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    readings_series(db, n=40, step_min=6, sensor_row=sen, start=t0)
    db.commit()
    split = build_features(db, max_rows=8000, test_months=3)
    assert split.n_total > 0
    assert not split.train.empty or not split.test.empty
    featured = split.train if not split.train.empty else split.test
    for col in FEATURE_COLUMNS + [LABEL_COLUMN]:
        assert col in featured.columns
