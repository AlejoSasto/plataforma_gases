"""Servicio de alertas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.alerts.rules import build_alert_payload, should_create_alert
from app.modules.audit.service import record_audit
from app.modules.predictions.models import Prediction
from app.modules.sensors_ingestion.models import GasReading, Sensor, Site
from app.modules.users.models import User
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.formatting import (
    display_gas,
    display_sensor_code,
    display_site_name,
    format_datetime_short,
)


def evaluate_and_create_alert(
    db: Session,
    prediction: Prediction,
    reading: GasReading,
) -> Alert | None:
    if not should_create_alert(prediction, reading):
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
    payload = build_alert_payload(prediction, reading, sensor)
    alert = Alert(
        prediction_id=prediction.id,
        gas_reading_id=reading.id,
        sensor_id=reading.sensor_id,
        level=payload["level"],
        message=payload["message"],
        recommendation=payload["recommendation"],
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
    if site_id is not None:
        q = q.join(Sensor, Sensor.id == Alert.sensor_id).filter(Sensor.site_id == site_id)
    total = q.count()
    items = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def alert_to_dict(db: Session, alert: Alert) -> dict[str, Any]:
    sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
    site_name = None
    if sensor is not None:
        site = db.query(Site).filter(Site.id == sensor.site_id).first()
        site_name = display_site_name(site.name) if site else None
    return {
        "id": alert.id,
        "prediction_id": alert.prediction_id,
        "gas_reading_id": alert.gas_reading_id,
        "sensor_id": alert.sensor_id,
        "sensor_code": display_sensor_code(sensor.code) if sensor else None,
        "gas_type": display_gas(sensor.gas_type) if sensor else None,
        "site_name": site_name,
        "level": alert.level,
        "message": alert.message,
        "recommendation": alert.recommendation,
        "status": alert.status,
        "created_at": format_datetime_short(alert.created_at),
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_at": format_datetime_short(alert.acknowledged_at),
        "resolved_at": format_datetime_short(alert.resolved_at),
        "resolution_note": alert.resolution_note,
    }
