"""Servicio de usuarios."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.audit.service import record_audit
from app.modules.users import repository as users_repo
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserRolesUpdate, UserUpdate
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.pagination import Page, PageParams


def _to_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": user.role_names,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def list_users(db: Session, params: PageParams) -> Page[dict]:
    items, total = users_repo.list_users(db, offset=params.offset, limit=params.page_size)
    return Page(
        items=[_to_response(u) for u in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def get_user(db: Session, user_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")
    return _to_response(user)


def create_user(db: Session, data: UserCreate, actor_id: int) -> dict:
    if users_repo.get_by_email(db, data.email) is not None:
        raise ValidationError("El email ya está registrado")

    roles = users_repo.get_roles_by_ids(db, data.role_ids)
    if len(roles) != len(set(data.role_ids)):
        raise ValidationError("Uno o más roles no existen")

    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        is_active=data.is_active,
        roles=roles,
    )
    users_repo.create_user(db, user)
    record_audit(
        db,
        action="user.create",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"email": user.email, "role_ids": data.role_ids},
    )
    db.commit()
    user = users_repo.get_user(db, user.id)
    assert user is not None
    return _to_response(user)


def update_user(db: Session, user_id: int, data: UserUpdate, actor_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")

    payload = data.model_dump(exclude_unset=True)
    if "email" in payload and payload["email"]:
        existing = users_repo.get_by_email(db, payload["email"])
        if existing is not None and existing.id != user.id:
            raise ValidationError("El email ya está registrado")
        user.email = payload["email"].lower()
    if "full_name" in payload and payload["full_name"] is not None:
        user.full_name = payload["full_name"]
    if "is_active" in payload and payload["is_active"] is not None:
        user.is_active = payload["is_active"]
    if "password" in payload and payload["password"]:
        user.password_hash = hash_password(payload["password"])

    db.add(user)
    record_audit(
        db,
        action="user.update",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        metadata={k: v for k, v in payload.items() if k != "password"},
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user)


def soft_delete_user(db: Session, user_id: int, actor_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")
    user.is_active = False
    db.add(user)
    record_audit(
        db,
        action="user.deactivate",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user)


def set_roles(db: Session, user_id: int, data: UserRolesUpdate, actor_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")

    roles = users_repo.get_roles_by_ids(db, data.role_ids)
    if len(roles) != len(set(data.role_ids)):
        raise ValidationError("Uno o más roles no existen")

    users_repo.set_user_roles(db, user, roles)
    record_audit(
        db,
        action="user.roles_update",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"role_ids": data.role_ids},
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user)
