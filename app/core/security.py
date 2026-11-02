"""Seguridad: hashing de contraseñas y JWT (access + refresh)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def hash_token(raw: str) -> str:
    """Hash SHA-256 de un token opaco (refresh) para almacenar en DB."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: int | str,
    roles: Sequence[str] | None = None,
    permissions: Sequence[str] | None = None,
    expires_minutes: Optional[int] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "roles": list(roles or []),
        "permissions": list(permissions or []),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int | str) -> tuple[str, datetime]:
    """
    Genera un refresh token opaco y su fecha de expiración (turno de 8 h).
    El caller debe persistir hash_token(raw) en refresh_tokens.
    """
    raw = secrets.token_urlsafe(48)
    hours = getattr(settings, "refresh_token_expire_hours", None) or 8
    expires_at = datetime.now(timezone.utc) + timedelta(hours=int(hours))
    _ = user_id
    return raw, expires_at


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") not in (None, "access"):
            return None
        return payload
    except JWTError:
        return None


# Alias de compatibilidad con el esqueleto del Plan 01.
decode_token = decode_access_token


def cookie_secure() -> bool:
    return settings.environment == "prod"
