"""Contrato de series/gráficos con datos históricos (Plan 23 F7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.dashboard import service as dash_service
from app.modules.forecasting.service import reference_time
from app.shared import present
from tests import factories as f

pytestmark = [pytest.mark.plan23, pytest.mark.plan]


def test_series_uses_reference_time_not_wall_clock(db) -> None:
    past = datetime(2025, 12, 11, 14, 0, tzinfo=timezone.utc)
    s = f.sensor(db, code="CHART#REF", gas_type="CH4")
    for i in range(12):
        f.reading(
            db,
            sensor_row=s,
            leyendo=0.2 + i * 0.01,
            when=past - timedelta(minutes=6 * (11 - i)),
        )
    db.flush()

    ref = reference_time(db, s.id)
    assert abs((ref - past).total_seconds()) < 1

    series = dash_service.series_for_sensor(db, s.id, hours=2)
    assert len(series["points"]) >= 10
    assert series["reference_time"] == ref.isoformat()
    assert series["data_until"] == ref.isoformat()


def test_chart_now_and_next_nonempty_for_historical(db) -> None:
    past = datetime(2025, 11, 14, 10, 0, tzinfo=timezone.utc)
    s = f.sensor(db, code="CHART#NOW", gas_type="CO", unit="ppm")
    for i in range(8):
        f.reading(
            db,
            sensor_row=s,
            leyendo=10 + i,
            when=past - timedelta(minutes=6 * (7 - i)),
        )
    db.flush()

    payload = present.chart_now_and_next(db, s.id, hours=1.0)
    assert payload["measured"], "debe devolver lecturas ancladas al último dato"
    assert payload["reference_time"] == payload["now"]
    assert payload["data_until"]
    assert payload["empty_message"] is None
