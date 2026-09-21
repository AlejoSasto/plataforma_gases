"""Repositorio de usuarios."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.modules.roles_permissions.models import Role
from app.modules.users.models import User


def list_users(db: Session, *, offset: int, limit: int) -> tuple[list[User], int]:
    total = db.query(User).count()
    items = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .order_by(User.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_user(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def create_user(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def set_user_roles(db: Session, user: User, roles: list[Role]) -> User:
    user.roles = roles
    db.add(user)
    db.flush()
    return (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.permissions))
        .filter(User.id == user.id)
        .one()
    )


def get_roles_by_ids(db: Session, role_ids: list[int]) -> list[Role]:
    if not role_ids:
        return []
    return db.query(Role).filter(Role.id.in_(role_ids)).all()
