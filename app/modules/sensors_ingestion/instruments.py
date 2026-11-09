"""Equipos reales: un instrumento por número de serie, sin zona inventada."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.sensors_ingestion.models import GasReading, Instrument, Sensor


def infer_model(serial: str, source: str | None = None) -> str | None:
    blob = f"{serial} {source or ''}".upper()
    if "MX6" in blob:
        return "MX6"
    return None


def ensure_instrument(db: Session, serial: str, *, source: str | None = None) -> Instrument:
    key = (serial or "").strip() or "SIN_SERIE"
    row = db.query(Instrument).filter(Instrument.serial == key).one_or_none()
    if row is None:
        row = Instrument(serial=key, model=infer_model(key, source))
        db.add(row)
        db.flush()
    elif row.model is None:
        row.model = infer_model(key, source)
    return row


def attach_sensor(db: Session, sensor: Sensor, *, source: str | None = None) -> Instrument:
    instrument = ensure_instrument(db, sensor.code, source=source)
    sensor.instrument_id = instrument.id
    return instrument


def backfill_instruments(db: Session) -> int:
    n = 0
    for sensor in db.query(Sensor).all():
        attach_sensor(db, sensor)
        n += 1
    spans = (
        db.query(
            Sensor.instrument_id,
            func.min(GasReading.tiempo_inicio),
            func.max(GasReading.tiempo_inicio),
        )
        .join(GasReading, GasReading.sensor_id == Sensor.id)
        .filter(Sensor.instrument_id.is_not(None))
        .group_by(Sensor.instrument_id)
        .all()
    )
    for instrument_id, first, last in spans:
        row = db.get(Instrument, instrument_id)
        if row is None:
            continue
        row.first_seen = first
        row.last_seen = last
    db.flush()
    return n
