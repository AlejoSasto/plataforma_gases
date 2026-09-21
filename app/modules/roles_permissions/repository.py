"""Repositorio de roles y permisos."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.modules.roles_permissions.models import Permission, Role


def list_roles(db: Session) -> list[Role]:
    return (
        db.query(Role)
        .options(joinedload(Role.permissions))
        .order_by(Role.id)
        .all()
    )


def get_role(db: Session, role_id: int) -> Role | None:
    return (
        db.query(Role)
        .options(joinedload(Role.permissions))
        .filter(Role.id == role_id)
        .first()
    )


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).first()


def list_permissions(db: Session) -> list[Permission]:
    return db.query(Permission).order_by(Permission.code).all()


def get_permissions_by_ids(db: Session, permission_ids: list[int]) -> list[Permission]:
    if not permission_ids:
        return []
    return db.query(Permission).filter(Permission.id.in_(permission_ids)).all()


def create_role(db: Session, role: Role) -> Role:
    db.add(role)
    db.flush()
    return role
