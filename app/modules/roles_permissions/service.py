"""Servicio de roles y permisos."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.audit.service import record_audit
from app.modules.roles_permissions import repository as roles_repo
from app.modules.roles_permissions.models import Role
from app.modules.roles_permissions.schemas import RoleCreate, RoleUpdate
from app.shared.exceptions import NotFoundError, ValidationError


def _role_to_dict(role: Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": [p.code for p in role.permissions],
    }


def list_roles(db: Session) -> list[dict]:
    return [_role_to_dict(r) for r in roles_repo.list_roles(db)]


def list_permissions(db: Session) -> list[dict]:
    return [
        {"id": p.id, "code": p.code, "description": p.description}
        for p in roles_repo.list_permissions(db)
    ]


def create_role(db: Session, data: RoleCreate, actor_id: int) -> dict:
    if roles_repo.get_role_by_name(db, data.name) is not None:
        raise ValidationError("Ya existe un rol con ese nombre")

    permissions = roles_repo.get_permissions_by_ids(db, data.permission_ids)
    if len(permissions) != len(set(data.permission_ids)):
        raise ValidationError("Uno o más permisos no existen")

    role = Role(name=data.name, description=data.description, permissions=permissions)
    roles_repo.create_role(db, role)
    record_audit(
        db,
        action="role.create",
        user_id=actor_id,
        resource_type="role",
        resource_id=role.id,
        metadata={"name": role.name, "permission_ids": data.permission_ids},
    )
    db.commit()
    role = roles_repo.get_role(db, role.id)
    assert role is not None
    return _role_to_dict(role)


def update_role(db: Session, role_id: int, data: RoleUpdate, actor_id: int) -> dict:
    role = roles_repo.get_role(db, role_id)
    if role is None:
        raise NotFoundError("Rol no encontrado")

    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"]:
        existing = roles_repo.get_role_by_name(db, payload["name"])
        if existing is not None and existing.id != role.id:
            raise ValidationError("Ya existe un rol con ese nombre")
        role.name = payload["name"]
    if "description" in payload:
        role.description = payload["description"]
    if "permission_ids" in payload and payload["permission_ids"] is not None:
        permissions = roles_repo.get_permissions_by_ids(db, payload["permission_ids"])
        if len(permissions) != len(set(payload["permission_ids"])):
            raise ValidationError("Uno o más permisos no existen")
        role.permissions = permissions

    db.add(role)
    record_audit(
        db,
        action="role.update",
        user_id=actor_id,
        resource_type="role",
        resource_id=role.id,
        metadata=payload,
    )
    db.commit()
    role = roles_repo.get_role(db, role_id)
    assert role is not None
    return _role_to_dict(role)
