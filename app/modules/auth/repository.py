"""Repositorio de autenticación (refresh tokens)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.modules.roles_permissions.models import Role
from app.modules.users.models import RefreshToken, User


def get_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.email == email.lower())
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )


def create_refresh_token_row(
    db: Session,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip: str | None = None,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def get_refresh_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return (
        db.query(RefreshToken)
        .options(
            joinedload(RefreshToken.user)
            .joinedload(User.roles)
            .joinedload(Role.permissions)
        )
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )


def revoke_refresh(db: Session, row: RefreshToken) -> None:
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.add(row)
        db.flush()


def revoke_all_for_user(db: Session, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    rows = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        row.revoked_at = now
        db.add(row)
    db.flush()
    return len(rows)


def list_sessions(db: Session, user_id: int) -> list[RefreshToken]:
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id)
        .order_by(RefreshToken.last_used_at.desc().nullslast())
        .all()
    )
