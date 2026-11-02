"""Servicio de usuarios."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.passwords import validate_password
from app.core.security import hash_password
from app.modules.audit.service import record_audit
from app.modules.users import repository as users_repo
from app.modules.users.models import User, UserSiteScope
from app.modules.users.schemas import UserCreate, UserRolesUpdate, UserSitesUpdate, UserUpdate
from app.shared.access import role_label
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.pagination import Page, PageParams


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_locked(user: User) -> bool:
    until = user.locked_until
    if until is None:
        return False
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > _now()


def _status_of(user: User) -> str:
    if not user.is_active:
        return "desactivado"
    if _is_locked(user):
        return "bloqueado"
    if user.must_change_password and user.last_login_at is None:
        return "invitado"
    return "activo"


def _site_ids(db: Session, user_id: int) -> list[int]:
    rows = db.query(UserSiteScope).filter(UserSiteScope.user_id == user_id).all()
    return [r.site_id for r in rows]


def _to_response(user: User, db: Session | None = None) -> dict:
    site_ids: list[int] = []
    if db is not None:
        site_ids = _site_ids(db, user.id)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": user.role_names,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
        "must_change_password": bool(user.must_change_password),
        "locked": _is_locked(user),
        "site_ids": site_ids,
        "status": _status_of(user),
    }


def list_users(db: Session, params: PageParams) -> Page[dict]:
    items, total = users_repo.list_users(db, offset=params.offset, limit=params.page_size)
    return Page(
        items=[_to_response(u, db) for u in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def get_user(db: Session, user_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")
    return _to_response(user, db)


def create_user(db: Session, data: UserCreate, actor_id: int) -> dict:
    if users_repo.get_by_email(db, data.email) is not None:
        raise ValidationError("El email ya está registrado")

    err = validate_password(data.password, email=data.email, full_name=data.full_name)
    if err:
        raise ValidationError(err)

    roles = users_repo.get_roles_by_ids(db, data.role_ids)
    if len(roles) != len(set(data.role_ids)):
        raise ValidationError("Uno o más roles no existen")

    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        is_active=data.is_active,
        must_change_password=True,
        roles=roles,
    )
    users_repo.create_user(db, user)
    for sid in data.site_ids or []:
        db.add(UserSiteScope(user_id=user.id, site_id=int(sid)))
    labels = ", ".join(role_label(r.name) for r in roles) or "sin rol"
    record_audit(
        db,
        action="user.create",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"email": user.email, "role_ids": data.role_ids},
        details=f"creó a {user.full_name} como {labels}",
    )
    db.commit()
    user = users_repo.get_user(db, user.id)
    assert user is not None
    return _to_response(user, db)


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
        err = validate_password(payload["password"], email=user.email, full_name=user.full_name)
        if err:
            raise ValidationError(err)
        user.password_hash = hash_password(payload["password"])
        user.must_change_password = True

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
    return _to_response(user, db)


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
    return _to_response(user, db)


def set_roles(db: Session, user_id: int, data: UserRolesUpdate, actor_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")

    roles = users_repo.get_roles_by_ids(db, data.role_ids)
    if len(roles) != len(set(data.role_ids)):
        raise ValidationError("Uno o más roles no existen")

    users_repo.set_user_roles(db, user, roles)
    labels = ", ".join(role_label(r.name) for r in roles) or "sin rol"
    record_audit(
        db,
        action="user.role_changed",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"role_ids": data.role_ids},
        details=f"cambió el rol de {user.full_name} a {labels}",
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user, db)


def set_sites(db: Session, user_id: int, data: UserSitesUpdate, actor_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")
    db.query(UserSiteScope).filter(UserSiteScope.user_id == user_id).delete()
    for sid in data.site_ids:
        db.add(UserSiteScope(user_id=user_id, site_id=int(sid)))
    record_audit(
        db,
        action="user.scope_changed",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        metadata={"site_ids": data.site_ids},
        details=f"asignó zonas a {user.full_name}",
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user, db)


def unlock_user(db: Session, user_id: int, actor_id: int) -> dict:
    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")
    user.failed_login_count = 0
    user.locked_until = None
    db.add(user)
    record_audit(
        db,
        action="user.unlocked",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        details=f"desbloqueó a {user.full_name}",
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user, db)


def force_password_change(db: Session, user_id: int, actor_id: int) -> dict:
    from app.modules.auth import repository as auth_repo

    user = users_repo.get_user(db, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado")
    user.must_change_password = True
    db.add(user)
    auth_repo.revoke_all_for_user(db, user.id)
    record_audit(
        db,
        action="user.update",
        user_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        details=f"pidió a {user.full_name} cambiar la contraseña",
    )
    db.commit()
    user = users_repo.get_user(db, user_id)
    assert user is not None
    return _to_response(user, db)
