"""Fixtures compartidas para tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.modules.roles_permissions.models import Role
from app.modules.users.models import User
from scripts.seed_roles_permissions import seed


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_roles(db: Session) -> None:
    seed(db)


def _ensure_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role_name: str,
) -> User:
    role = db.query(Role).filter(Role.name == role_name).one()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            roles=[role],
        )
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.full_name = full_name
        user.is_active = True
        user.roles = [role]
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def admin_user(db: Session, seeded_roles: None) -> tuple[User, str]:
    password = "AdminPass123!"
    user = _ensure_user(
        db,
        email="test.admin@example.com",
        password=password,
        full_name="Test Admin",
        role_name="admin",
    )
    return user, password


@pytest.fixture()
def operador_user(db: Session, seeded_roles: None) -> tuple[User, str]:
    password = "OperadorPass123!"
    user = _ensure_user(
        db,
        email="test.operador@example.com",
        password=password,
        full_name="Test Operador",
        role_name="operador_mina",
    )
    return user, password
