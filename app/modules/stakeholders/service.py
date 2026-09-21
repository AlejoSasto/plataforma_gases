"""Servicio de stakeholders y resolución de destinatarios."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.sensors_ingestion.models import Sensor
from app.modules.stakeholders.models import (
    Stakeholder,
    StakeholderSubscription,
    StakeholderUser,
)
from app.modules.stakeholders.notifier import notify_alert_recipients
from app.shared.exceptions import NotFoundError, ValidationError

LEVEL_RANK = {
    "NORMAL": 0,
    "PRECAUCION": 1,
    "ALERTA": 2,
    "CRITICO": 3,
}


def _rank(level: str) -> int:
    return LEVEL_RANK.get((level or "").upper(), 0)


def create_stakeholder(db: Session, data: dict[str, Any]) -> Stakeholder:
    if data.get("type") not in {"interno", "externo"}:
        raise ValidationError("type debe ser interno o externo")
    row = Stakeholder(
        name=data["name"],
        type=data["type"],
        organization=data.get("organization"),
        email=data.get("email"),
        phone=data.get("phone"),
        notify_channels=data.get("notify_channels") or ["email"],
    )
    db.add(row)
    db.flush()
    user_id = data.get("user_id")
    if user_id is not None:
        db.add(StakeholderUser(stakeholder_id=row.id, user_id=int(user_id)))
        db.flush()
    db.commit()
    db.refresh(row)
    return row


def update_stakeholder(db: Session, stakeholder_id: int, data: dict[str, Any]) -> Stakeholder:
    row = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if row is None:
        raise NotFoundError("Stakeholder no encontrado")
    for field in ("name", "type", "organization", "email", "phone", "notify_channels"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_stakeholder(db: Session, stakeholder_id: int) -> None:
    row = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if row is None:
        raise NotFoundError("Stakeholder no encontrado")
    db.delete(row)
    db.commit()


def list_stakeholders(db: Session) -> list[Stakeholder]:
    return db.query(Stakeholder).order_by(Stakeholder.id).all()


def get_stakeholder(db: Session, stakeholder_id: int) -> Stakeholder:
    row = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if row is None:
        raise NotFoundError("Stakeholder no encontrado")
    return row


def add_subscription(db: Session, stakeholder_id: int, data: dict[str, Any]) -> StakeholderSubscription:
    get_stakeholder(db, stakeholder_id)
    min_level = (data.get("min_level") or "ALERTA").upper()
    if min_level not in LEVEL_RANK:
        raise ValidationError("min_level inválido")
    sub = StakeholderSubscription(
        stakeholder_id=stakeholder_id,
        site_id=data.get("site_id"),
        sensor_id=data.get("sensor_id"),
        min_level=min_level,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def list_subscriptions(db: Session, stakeholder_id: int) -> list[StakeholderSubscription]:
    get_stakeholder(db, stakeholder_id)
    return (
        db.query(StakeholderSubscription)
        .filter(StakeholderSubscription.stakeholder_id == stakeholder_id)
        .order_by(StakeholderSubscription.id)
        .all()
    )


def delete_subscription(db: Session, subscription_id: int) -> None:
    sub = (
        db.query(StakeholderSubscription)
        .filter(StakeholderSubscription.id == subscription_id)
        .first()
    )
    if sub is None:
        raise NotFoundError("Suscripción no encontrada")
    db.delete(sub)
    db.commit()


def get_recipients_for_alert(db: Session, alert: Alert) -> list[Stakeholder]:
    sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
    if sensor is None:
        return []
    site_id = sensor.site_id
    alert_rank = _rank(alert.level)

    subs = db.query(StakeholderSubscription).all()
    matched_ids: set[int] = set()
    for sub in subs:
        if _rank(sub.min_level) > alert_rank:
            continue
        if sub.sensor_id is not None and sub.sensor_id != alert.sensor_id:
            continue
        if sub.site_id is not None and sub.site_id != site_id:
            continue
        # Si ambos null → suscripción global (todos los sitios)
        matched_ids.add(sub.stakeholder_id)

    if not matched_ids:
        return []
    return (
        db.query(Stakeholder)
        .filter(Stakeholder.id.in_(matched_ids))
        .order_by(Stakeholder.id)
        .all()
    )


def dispatch_alert_notifications(db: Session, alert: Alert) -> int:
    recipients = get_recipients_for_alert(db, alert)
    return notify_alert_recipients(db, alert, recipients)


def stakeholder_ids_for_user(db: Session, user_id: int) -> list[int]:
    links = db.query(StakeholderUser).filter(StakeholderUser.user_id == user_id).all()
    return [link.stakeholder_id for link in links]


def alert_ids_visible_to_user(db: Session, user_id: int) -> Optional[set[int]]:
    """
    None = sin restricción.
    set = solo esas alertas (rol interesado vinculado a stakeholder).
    """
    from app.modules.users.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return set()
    roles = set(user.role_names)
    if "interesado" not in roles:
        return None
    # Roles operativos / admin ven todo
    if roles & {"admin", "operador_mina", "ingeniero_datos", "auditor"}:
        return None

    s_ids = stakeholder_ids_for_user(db, user_id)
    if not s_ids:
        return set()

    subs = (
        db.query(StakeholderSubscription)
        .filter(StakeholderSubscription.stakeholder_id.in_(s_ids))
        .all()
    )
    if not subs:
        return set()

    alerts = db.query(Alert).all()
    visible: set[int] = set()
    for alert in alerts:
        sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
        if sensor is None:
            continue
        for sub in subs:
            if _rank(sub.min_level) > _rank(alert.level):
                continue
            if sub.sensor_id is not None and sub.sensor_id != alert.sensor_id:
                continue
            if sub.site_id is not None and sub.site_id != sensor.site_id:
                continue
            visible.add(alert.id)
            break
    return visible


def stakeholder_to_dict(row: Stakeholder) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "organization": row.organization,
        "email": row.email,
        "phone": row.phone,
        "notify_channels": row.notify_channels or ["email"],
        "created_at": row.created_at,
        "user_ids": [link.user_id for link in row.user_links],
    }


def subscription_to_dict(sub: StakeholderSubscription) -> dict[str, Any]:
    return {
        "id": sub.id,
        "stakeholder_id": sub.stakeholder_id,
        "site_id": sub.site_id,
        "sensor_id": sub.sensor_id,
        "min_level": sub.min_level,
        "created_at": sub.created_at,
    }
