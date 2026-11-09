"""Servicio de alertas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.alerts.rules import build_alert_payload, should_create_alert
from app.modules.audit.service import record_audit
from app.modules.forecasting.models import Forecast
from app.modules.sensors_ingestion.models import GasReading, Sensor, Site
from app.modules.users.models import User
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.formatting import (
    display_gas,
    display_sensor_code,
    display_site_name,
)


def evaluate_and_create_alert(
    db: Session,
    reading: GasReading,
    forecast: Forecast | None = None,
) -> Alert | None:
    if not should_create_alert(reading, forecast):
        return None

    existing = (
        db.query(Alert)
        .filter(
            Alert.gas_reading_id == reading.id,
            Alert.status.in_(["abierta", "reconocida"]),
        )
        .first()
    )
    if existing is not None:
        return existing

    sensor = db.query(Sensor).filter(Sensor.id == reading.sensor_id).one()
    payload = build_alert_payload(reading, sensor, forecast)
    alert = Alert(
        forecast_id=forecast.id if forecast is not None else None,
        gas_reading_id=reading.id,
        sensor_id=reading.sensor_id,
        kind=payload["kind"],
        level=payload["level"],
        message=payload["message"],
        recommendation=payload["recommendation"],
        plain_message=payload["plain_message"],
        plain_recommendation=payload["plain_recommendation"],
        status="abierta",
    )
    db.add(alert)
    db.flush()
    try:
        from app.modules.stakeholders.service import dispatch_alert_notifications

        dispatch_alert_notifications(db, alert)
    except Exception:  # noqa: BLE001 — no fallar creación de alerta por notificación
        pass
    return alert


def acknowledge_alert(db: Session, alert_id: int, user: User) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise NotFoundError("Alerta no encontrada")
    if alert.status == "resuelta":
        raise ValidationError("La alerta ya está resuelta")
    alert.status = "reconocida"
    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.add(alert)
    record_audit(
        db,
        action="alert.acknowledge",
        user_id=user.id,
        resource_type="alert",
        resource_id=alert.id,
    )
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(
    db: Session,
    alert_id: int,
    user: User,
    resolution_note: str | None = None,
) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise NotFoundError("Alerta no encontrada")
    alert.status = "resuelta"
    alert.resolved_by = user.id
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_note = resolution_note
    if alert.acknowledged_by is None:
        alert.acknowledged_by = user.id
        alert.acknowledged_at = datetime.now(timezone.utc)
    db.add(alert)
    record_audit(
        db,
        action="alert.resolve",
        user_id=user.id,
        resource_type="alert",
        resource_id=alert.id,
        metadata={"note": resolution_note},
    )
    db.commit()
    db.refresh(alert)
    return alert


def get_alert(db: Session, alert_id: int) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def list_alerts(
    db: Session,
    *,
    offset: int,
    limit: int,
    status: str | None = None,
    level: str | None = None,
    site_id: int | None = None,
    site_ids: set[int] | None = None,
    visible_ids: set[int] | None = None,
    origin: str | None = None,
) -> tuple[list[Alert], int]:
    q = db.query(Alert)
    if visible_ids is not None:
        if not visible_ids:
            return [], 0
        q = q.filter(Alert.id.in_(visible_ids))
    if status:
        q = q.filter(Alert.status == status)
    if origin:
        q = q.filter(Alert.origin == origin)
    if level:
        q = q.filter(Alert.level == level)
    if site_id is not None or site_ids is not None:
        q = q.join(Sensor, Sensor.id == Alert.sensor_id)
        if site_id is not None:
            q = q.filter(Sensor.site_id == site_id)
        if site_ids is not None:
            if not site_ids:
                return [], 0
            q = q.filter(Sensor.site_id.in_(site_ids))
    total = q.count()
    items = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def _source_file(db: Session, alert: Alert) -> str | None:
    if alert.gas_reading_id is None:
        return None
    from app.modules.sensors_ingestion.models import GasReading

    reading = db.get(GasReading, alert.gas_reading_id)
    return reading.source_file if reading else None


def search_for_assistant(
    db: Session,
    *,
    sensor_ids: list[int],
    start: datetime | None,
    end: datetime | None,
    gas: str | None,
    nivel: str | None,
    origin: str | None,
    status: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Lista corta de avisos para el asistente. Sin correos ni rutas de archivo."""
    from app.shared.access import canonical_role
    from app.shared.gas_catalog import canonicalize_gas_type

    del canonical_role
    if not sensor_ids:
        return []
    query = db.query(Alert).join(Sensor, Sensor.id == Alert.sensor_id)
    query = query.filter(Alert.sensor_id.in_(sensor_ids))
    if start is not None:
        query = query.filter(Alert.created_at >= start)
    if end is not None:
        query = query.filter(Alert.created_at <= end)
    if origin:
        query = query.filter(Alert.origin == origin)
    if status:
        query = query.filter(Alert.status == status)
    if nivel:
        query = query.filter(Alert.level.in_(_level_aliases(nivel)))
    rows = query.order_by(Alert.created_at.desc()).limit(max(limit * 4, limit)).all()
    gas_code = canonicalize_gas_type(gas) if gas else None
    items: list[dict[str, Any]] = []
    for alert in rows:
        sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
        if sensor is None:
            continue
        if gas_code and canonicalize_gas_type(sensor.gas_type) != gas_code:
            continue
        outcome = alert.outcome.outcome if alert.outcome is not None else "pendiente"
        items.append(
            {
                "aviso": alert.id,
                "fecha": alert.created_at.isoformat() if alert.created_at else None,
                "gas": display_gas(sensor.gas_type),
                "gas_code": canonicalize_gas_type(sensor.gas_type),
                "equipo": display_sensor_code(sensor.code),
                "nivel": alert.level,
                "tipo": "anticipado" if alert.kind != "confirmado" else "confirmado",
                "resultado": outcome,
                "origen": alert.origin,
                "estado": alert.status,
                "que_hacer": alert.plain_recommendation or alert.recommendation,
                "mensaje": alert.plain_message or alert.message,
            }
        )
        if len(items) >= limit:
            break
    return items


def detail_for_assistant(db: Session, alert_id: int, *, include_lineage: bool) -> dict[str, Any] | None:
    alert = get_alert(db, alert_id)
    if alert is None:
        return None
    data = alert_to_dict(db, alert)
    reading = None
    if alert.gas_reading_id is not None:
        reading = db.get(GasReading, alert.gas_reading_id)
    outcome = alert.outcome.outcome if alert.outcome is not None else "pendiente"
    payload = {
        "aviso": alert.id,
        "fecha": data.get("created_at").isoformat() if data.get("created_at") else None,
        "gas": data.get("gas_type"),
        "equipo": data.get("sensor_code"),
        "nivel": alert.level,
        "tipo": "anticipado" if alert.kind != "confirmado" else "confirmado",
        "origen": alert.origin,
        "estado": alert.status,
        "mensaje": alert.plain_message or alert.message,
        "por_que": alert.plain_message or alert.message,
        "que_hacer": alert.plain_recommendation or alert.recommendation,
        "nota_cierre": alert.resolution_note,
        "resultado": outcome,
        "lectura": float(reading.leyendo) if reading is not None else None,
        "lectura_en": reading.tiempo_inicio.isoformat() if reading is not None else None,
    }
    if include_lineage:
        payload["linaje"] = "El origen del aviso está en la ficha, sin rutas internas."
    return payload


def _level_aliases(nivel: str) -> list[str]:
    key = nivel.strip().casefold()
    groups = {
        "vigilar": ["vigilar", "PRECAUCION", "precaucion", "Vigilar"],
        "actuar": ["actuar", "ALERTA", "alerta", "Actuar ya"],
        "evacuar": ["evacuar", "CRITICO", "critico", "Evacuar"],
        "normal": ["normal", "NORMAL", "Normal"],
        "precaucion": ["vigilar", "PRECAUCION", "precaucion"],
        "alerta": ["actuar", "ALERTA", "alerta"],
        "critico": ["evacuar", "CRITICO", "critico"],
    }
    return groups.get(key, [nivel])


def alert_to_dict(db: Session, alert: Alert) -> dict[str, Any]:
    sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
    site_name = None
    if sensor is not None:
        site = db.query(Site).filter(Site.id == sensor.site_id).first()
        site_name = display_site_name(site.name) if site else None
    ack_name = None
    if alert.acknowledged_by:
        who = db.query(User).filter(User.id == alert.acknowledged_by).first()
        ack_name = who.full_name if who else None
    return {
        "id": alert.id,
        "forecast_id": alert.forecast_id,
        "kind": alert.kind,
        "gas_reading_id": alert.gas_reading_id,
        "sensor_id": alert.sensor_id,
        "sensor_code": display_sensor_code(sensor.code) if sensor else None,
        "gas_type": display_gas(sensor.gas_type) if sensor else None,
        "site_name": site_name,
        "level": alert.level,
        "message": alert.message,
        "recommendation": alert.recommendation,
        "plain_message": alert.plain_message,
        "plain_recommendation": alert.plain_recommendation,
        "expected_at": alert.expected_at,
        "status": alert.status,
        "created_at": alert.created_at,
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_name": ack_name,
        "acknowledged_at": alert.acknowledged_at,
        "resolved_at": alert.resolved_at,
        "resolution_note": alert.resolution_note,
        "origin": alert.origin,
        "human_handled": alert.human_handled,
        "closed_by": alert.closed_by,
        "source_file": _source_file(db, alert),
    }
