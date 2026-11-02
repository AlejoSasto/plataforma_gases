"""Fábricas mínimas para pruebas (Plan 20 F1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.alerts.models import Alert
from app.modules.roles_permissions.models import Role
from app.modules.sensors_ingestion.models import GasReading, Sensor, Site
from app.modules.users.models import User, UserSiteScope


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def site(db: Session, *, name: str = "Frente 3") -> Site:
    row = db.query(Site).filter(Site.name == name).first()
    if row is None:
        row = Site(name=name, description="Zona de prueba")
        db.add(row)
        db.flush()
    return row


def sensor(
    db: Session,
    *,
    code: str = "P20#CH4",
    gas_type: str = "CH4",
    unit: str = "%vol",
    site_row: Site | None = None,
) -> Sensor:
    site_row = site_row or site(db)
    row = db.query(Sensor).filter(Sensor.code == code, Sensor.gas_type == gas_type).first()
    if row is None:
        row = Sensor(site_id=site_row.id, code=code, gas_type=gas_type, unit=unit, kind="fijo")
        db.add(row)
        db.flush()
    return row


def reading(
    db: Session,
    *,
    sensor_row: Sensor | None = None,
    leyendo: float = 0.4,
    when: datetime | None = None,
    alarma: str | None = None,
) -> GasReading:
    sensor_row = sensor_row or sensor(db)
    when = when or utcnow()
    row = GasReading(
        sensor_id=sensor_row.id,
        leyendo=leyendo,
        unidad=sensor_row.unit,
        value_canonical=leyendo,
        unit_canonical=sensor_row.unit,
        alarma=alarma,
        temperatura=20.0,
        tiempo_inicio=when,
        is_synthetic=False,
        quality_status="ok",
    )
    db.add(row)
    db.flush()
    return row


def readings_series(
    db: Session,
    *,
    n: int = 24,
    step_min: int = 6,
    sensor_row: Sensor | None = None,
    start: datetime | None = None,
    values: list[float] | None = None,
) -> list[GasReading]:
    sensor_row = sensor_row or sensor(db)
    start = start or (utcnow() - timedelta(minutes=step_min * n))
    out: list[GasReading] = []
    for i in range(n):
        val = values[i] if values and i < len(values) else 0.3 + (i % 5) * 0.02
        out.append(
            reading(
                db,
                sensor_row=sensor_row,
                leyendo=val,
                when=start + timedelta(minutes=step_min * i),
            )
        )
    return out


def user_with_role(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role_name: str,
    site_ids: list[int] | None = None,
) -> User:
    role = db.query(Role).filter(Role.name == role_name).one()
    row = db.query(User).filter(User.email == email).first()
    if row is None:
        row = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            roles=[role],
        )
        db.add(row)
        db.flush()
    else:
        row.password_hash = hash_password(password)
        row.full_name = full_name
        row.is_active = True
        row.roles = [role]
        db.add(row)
        db.flush()
    if site_ids is not None:
        db.query(UserSiteScope).filter(UserSiteScope.user_id == row.id).delete()
        for sid in site_ids:
            db.add(UserSiteScope(user_id=row.id, site_id=int(sid)))
        db.flush()
    return row


def alert_row(
    db: Session,
    *,
    sensor_row: Sensor | None = None,
    level: str = "ALERTA",
    reading_row: GasReading | None = None,
) -> Alert:
    sensor_row = sensor_row or sensor(db)
    reading_row = reading_row or reading(db, sensor_row=sensor_row, leyendo=2.0, alarma="HIGH")
    row = Alert(
        sensor_id=sensor_row.id,
        gas_reading_id=reading_row.id,
        kind="confirmado",
        level=level,
        message="Aviso de prueba",
        recommendation="Revisar ventilación",
        plain_message="Hay que revisar esta zona",
        plain_recommendation="Revisar la ventilación",
        status="abierta",
    )
    db.add(row)
    db.flush()
    return row


def payload_real_sample() -> dict[str, Any]:
    return {"source": "tests/fixtures/real_sample.csv", "is_synthetic": False}
