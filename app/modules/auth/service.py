"""Servicio de autenticación."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    cookie_secure,
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.modules.audit.service import record_audit
from app.modules.auth import repository as auth_repo
from app.modules.users.models import User
from app.shared.exceptions import UnauthorizedError


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    secure = cookie_secure()
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def _issue_tokens(db: Session, user: User, response: Response) -> None:
    access = create_access_token(
        user.id, roles=user.role_names, permissions=user.permission_codes
    )
    refresh_raw, expires_at = create_refresh_token(user.id)
    auth_repo.create_refresh_token_row(
        db, user_id=user.id, token_hash=hash_token(refresh_raw), expires_at=expires_at
    )
    _set_auth_cookies(response, access, refresh_raw)


def login(db: Session, *, email: str, password: str, response: Response) -> User:
    user = auth_repo.get_user_by_email(db, email.strip().lower())
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Email o contraseña incorrectos")
    if not user.is_active:
        raise UnauthorizedError("Usuario inactivo")

    _issue_tokens(db, user, response)
    record_audit(
        db,
        action="login",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def refresh(db: Session, *, refresh_raw: str | None, response: Response) -> User:
    if not refresh_raw:
        raise UnauthorizedError("Refresh token ausente")

    row = auth_repo.get_refresh_by_hash(db, hash_token(refresh_raw))
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None:
        raise UnauthorizedError("Refresh token inválido")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise UnauthorizedError("Refresh token expirado")

    user = row.user
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuario no encontrado o inactivo")

    auth_repo.revoke_refresh(db, row)
    _issue_tokens(db, user, response)
    db.commit()
    db.refresh(user)
    return user


def logout(db: Session, *, user: User | None, refresh_raw: str | None, response: Response) -> None:
    if refresh_raw:
        row = auth_repo.get_refresh_by_hash(db, hash_token(refresh_raw))
        if row is not None:
            auth_repo.revoke_refresh(db, row)

    if user is not None:
        record_audit(
            db,
            action="logout",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
        )

    _clear_auth_cookies(response)
    db.commit()


def user_to_me(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": user.role_names,
        "permissions": user.permission_codes,
    }
