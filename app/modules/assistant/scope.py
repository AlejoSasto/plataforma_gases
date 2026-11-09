"""Alcance del usuario para las consultas del asistente."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.sensors_ingestion.models import Instrument, Sensor
from app.modules.users.models import User, UserInstrumentScope
from app.shared.access import scoped_site_ids


def visible_sensors(db: Session, user: User) -> list[Sensor]:
    query = db.query(Sensor)
    site_scope = scoped_site_ids(db, user)
    if site_scope is not None:
        if not site_scope:
            return []
        query = query.filter(Sensor.site_id.in_(site_scope))
    roles = set(user.role_names)
    instrument_ids = [
        row[0]
        for row in db.query(UserInstrumentScope.instrument_id)
        .filter(UserInstrumentScope.user_id == user.id)
        .all()
    ]
    if instrument_ids and "admin" not in roles:
        query = query.filter(Sensor.instrument_id.in_(instrument_ids))
    return query.order_by(Sensor.code.asc()).all()


def visible_sensor_ids(db: Session, user: User) -> list[int]:
    return [row.id for row in visible_sensors(db, user)]


def resolve_equipo(db: Session, user: User, equipo: str) -> list[int] | dict[str, str]:
    """Ids de sensores del equipo, o un error en lenguaje natural."""
    needle = equipo.strip().casefold()
    if not needle:
        return {"error": "Dime qué equipo quieres consultar."}
    sensors = visible_sensors(db, user)
    matched = [row for row in sensors if needle in (row.code or "").casefold()]
    instrument_ids = {row.instrument_id for row in sensors if row.instrument_id}
    if instrument_ids:
        instruments = db.query(Instrument).filter(Instrument.id.in_(instrument_ids)).all()
        by_serial = {row.id for row in instruments if needle in (row.serial or "").casefold()}
        matched.extend(row for row in sensors if row.instrument_id in by_serial)
    if matched:
        return list(dict.fromkeys(row.id for row in matched))
    hidden_sensor = db.query(Sensor).filter(Sensor.code.ilike(f"%{equipo.strip()}%")).first()
    hidden_instrument = db.query(Instrument).filter(Instrument.serial.ilike(f"%{equipo.strip()}%")).first()
    if hidden_sensor is not None or hidden_instrument is not None:
        return {"error": "Ese equipo no está en tu alcance."}
    return {"error": "No encuentro ese equipo."}
