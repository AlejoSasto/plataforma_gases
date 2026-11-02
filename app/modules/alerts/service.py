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
) -> tuple[list[Alert], int]:
    q = db.query(Alert)
    if visible_ids is not None:
        if not visible_ids:
            return [], 0
        q = q.filter(Alert.id.in_(visible_ids))
    if status:
        q = q.filter(Alert.status == status)
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
    }
