"""Dispositivos de sala de control (Plan 19)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.modules.audit.service import record_audit
from app.modules.users.models import KioskDevice, User
from app.shared.exceptions import NotFoundError, PermissionDeniedError

KIOSK_COOKIE = "kiosk_token"


def create_device(db: Session, *, actor: User, name: str, site_ids: list[int] | None) -> tuple[KioskDevice, str]:
    raw = secrets.token_urlsafe(32)
    row = KioskDevice(
        name=name.strip() or "Pantalla de sala",
        token_hash=hash_token(raw),
        site_ids=site_ids or [],
        created_by=actor.id,
    )
    db.add(row)
    record_audit(db, action="kiosk.created", user_id=actor.id, metadata={"name": row.name})
    db.commit()
    db.refresh(row)
    return row, raw


def revoke_device(db: Session, *, actor: User, device_id: int) -> KioskDevice:
    row = db.query(KioskDevice).filter(KioskDevice.id == device_id).first()
    if row is None:
        raise NotFoundError("Pantalla no encontrada")
    row.revoked_at = datetime.now(timezone.utc)
    db.add(row)
    record_audit(db, action="kiosk.revoked", user_id=actor.id, resource_id=device_id)
    db.commit()
    db.refresh(row)
    return row


def get_active(db: Session, raw: str | None) -> KioskDevice | None:
    if not raw:
        return None
    row = db.query(KioskDevice).filter(KioskDevice.token_hash == hash_token(raw)).first()
    if row is None or row.revoked_at is not None:
        return None
    row.last_seen_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return row


def list_devices(db: Session) -> list[KioskDevice]:
    return db.query(KioskDevice).order_by(KioskDevice.created_at.desc()).all()


def require_kiosk(device: KioskDevice | None) -> KioskDevice:
    if device is None:
        raise PermissionDeniedError("Esta pantalla no está emparejada")
    return device
