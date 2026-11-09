"""Utilidades compartidas por las herramientas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.assistant.scope import resolve_equipo, visible_sensor_ids
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User


def validation_error(exc: ValidationError) -> dict[str, str]:
    messages = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", []))
        if "fecha" in str(err.get("msg", "")).lower() or loc in {"desde", "hasta"}:
            messages.append("La fecha debe ir como AAAA-MM-DD.")
        else:
            messages.append("Revisa el dato que pediste: no tiene el formato esperado.")
    return {"error": " ".join(dict.fromkeys(messages)) or "No entendí los datos de la consulta."}


def envelope(
    *,
    data_until: str | None,
    historic: bool,
    clamped: bool,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "data_until": data_until,
        "historic": historic,
        "clamped": clamped,
    }
    body.update(payload)
    return body


def period_for(
    db: Session,
    user: User,
    inicio: datetime | None,
    fin: datetime | None,
    sensor_ids: list[int] | None = None,
) -> tuple[list[int], datetime, datetime, bool, str | None] | dict[str, str]:
    ids = visible_sensor_ids(db, user) if sensor_ids is None else sensor_ids
    if not ids:
        return {"error": "No hay equipos en tu alcance."}
    bounds = readings.data_bounds(db, ids)
    clamped = readings.clamp_period(inicio, fin, bounds)
    if isinstance(clamped, dict):
        return clamped
    start, end, was_clamped = clamped
    data_until = bounds[1].isoformat() if bounds[1] else None
    return ids, start, end, was_clamped, data_until


def equipo_ids(db: Session, user: User, equipo: str | None) -> list[int] | dict[str, str]:
    if not equipo:
        return visible_sensor_ids(db, user)
    return resolve_equipo(db, user, equipo)


def is_historic(end: datetime | None, data_until: str | None, origin: str | None) -> bool:
    if origin == "historico":
        return True
    if not data_until:
        return False
    try:
        latest = datetime.fromisoformat(data_until)
    except ValueError:
        return False
    today = datetime.now(latest.tzinfo).date() if latest.tzinfo else datetime.now().date()
    if latest.date() < today:
        return True
    if end is not None and end.date() < latest.date():
        return True
    return False
