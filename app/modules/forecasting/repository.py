"""Acceso ORM a forecasts."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.forecasting.models import Forecast, ForecastQuantile
from app.modules.sensors_ingestion.models import Sensor


def latest_for_sensor(db: Session, sensor_id: int) -> Optional[Forecast]:
    return (
        db.query(Forecast)
        .filter(Forecast.sensor_id == sensor_id)
        .order_by(Forecast.issued_at.desc())
        .first()
    )


def recent_for_sensor(db: Session, sensor_id: int, *, limit: int = 20) -> list[Forecast]:
    return (
        db.query(Forecast)
        .filter(Forecast.sensor_id == sensor_id)
        .order_by(Forecast.issued_at.desc())
        .limit(limit)
        .all()
    )


def list_forecasts(
    db: Session,
    *,
    offset: int,
    limit: int,
    sensor_id: int | None = None,
    site_id: int | None = None,
) -> tuple[list[Forecast], int]:
    q = db.query(Forecast)
    if sensor_id is not None:
        q = q.filter(Forecast.sensor_id == sensor_id)
    if site_id is not None:
        q = q.join(Sensor, Sensor.id == Forecast.sensor_id).filter(Sensor.site_id == site_id)
    total = q.count()
    items = q.order_by(Forecast.issued_at.desc()).offset(offset).limit(limit).all()
    return items, total


def get_forecast(db: Session, forecast_id: int) -> Optional[Forecast]:
    return db.query(Forecast).filter(Forecast.id == forecast_id).first()


def q50_for(forecast: Forecast, horizon_min: int | None = None) -> float | None:
    qs = list(forecast.quantiles or [])
    if not qs:
        return None
    if horizon_min is not None:
        match = next((q for q in qs if q.horizon_min == horizon_min), None)
        if match is not None:
            return match.q50
    qs_sorted = sorted(qs, key=lambda q: q.horizon_min)
    return qs_sorted[0].q50


def last_issued_at(db: Session, sensor_id: int) -> Optional[datetime]:
    row = latest_for_sensor(db, sensor_id)
    return None if row is None else row.issued_at
