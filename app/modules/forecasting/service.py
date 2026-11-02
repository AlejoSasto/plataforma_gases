"""Servicios de pronóstico (Plan 17) y referencia temporal de series (Plan 23 F7)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.forecasting import repository as repo
from app.modules.sensors_ingestion.models import GasReading
from app.shared.formatting import format_datetime_short, format_reading_value


def reference_time(db: Session, sensor_id: int | None = None) -> datetime:
    """Hora de referencia para series: último dato del sensor (o global), no el reloj."""
    q = db.query(func.max(GasReading.tiempo_inicio))
    if sensor_id is not None:
        q = q.filter(GasReading.sensor_id == sensor_id)
    mx = q.scalar()
    if mx is None:
        return datetime.now(timezone.utc)
    if mx.tzinfo is None:
        return mx.replace(tzinfo=timezone.utc)
    return mx


def list_forecasts(
    db: Session,
    *,
    offset: int,
    limit: int,
    sensor_id: int | None = None,
    site_id: int | None = None,
):
    return repo.list_forecasts(
        db, offset=offset, limit=limit, sensor_id=sensor_id, site_id=site_id
    )


def get_forecast(db: Session, forecast_id: int):
    return repo.get_forecast(db, forecast_id)


def recent_for_sensor(db: Session, sensor_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = repo.recent_for_sensor(db, sensor_id, limit=limit)
    out: list[dict[str, Any]] = []
    for f in rows:
        q50 = repo.q50_for(f)
        out.append(
            {
                "id": f.id,
                "status_level": f.status_level,
                "confidence": f.confidence,
                "exceed_prob": f.exceed_prob,
                "q50": format_reading_value(q50) if q50 is not None else None,
                "issued_at": format_datetime_short(f.issued_at),
                "model_id": f.model_id,
            }
        )
    return out
