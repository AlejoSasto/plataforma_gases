"""Dependencias FastAPI compartidas (DB + autenticación/autorización)."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import ACCESS_COOKIE, decode_access_token
from app.modules.roles_permissions.models import Role
from app.modules.users.models import User
from app.shared.exceptions import PermissionDeniedError, UnauthorizedError

__all__ = [
    "get_db",
    "db_session",
    "get_current_user",
    "require_permission",
    "CurrentUser",
    "DbSession",
]


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise UnauthorizedError("Token de acceso ausente")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Token de acceso inválido o expirado")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Token de acceso inválido") from exc

    user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuario no encontrado o inactivo")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(code: str) -> Callable[[User], User]:
    def _dependency(user: CurrentUser) -> User:
        if code not in user.permission_codes:
            raise PermissionDeniedError(f"Se requiere el permiso '{code}'")
        return user

    return _dependency
