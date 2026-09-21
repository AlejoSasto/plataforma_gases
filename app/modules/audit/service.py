"""Servicio de auditoría."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str | int] = None,
    metadata: Optional[dict[str, Any]] = None,
    details: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        metadata_=metadata,
        details=details,
    )
    db.add(entry)
    db.flush()
    return entry


def list_audit(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
) -> tuple[list[dict[str, Any]], int]:
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    total = q.count()
    rows = (
        q.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "metadata": r.metadata_,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return items, total
