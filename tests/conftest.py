"""Fixtures: DB de pruebas aislada, rollback por prueba (Plan 20 F1)."""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.db_urls import assert_isolated, load_urls

DEV_DATABASE_URL, TEST_DATABASE_URL = load_urls()
assert_isolated(DEV_DATABASE_URL, TEST_DATABASE_URL)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.core.config import get_settings
from app.core.database import engine, get_db
from app.core.rate_limit import reset as reset_rate_limit
from app.main import app
from app.modules.users.models import User
from scripts.seed_roles_permissions import seed
from tests.factories import user_with_role

get_settings.cache_clear()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "plan(n): pruebas del plan NN")
    config.addinivalue_line("markers", "plan20: plan 20 verificación")
    config.addinivalue_line("markers", "e2e: pruebas de extremo a extremo")
    config.addinivalue_line("markers", "perf: pruebas de rendimiento")


def pytest_sessionstart(session: pytest.Session) -> None:
    from scripts.ensure_test_db import ensure

    ensure(TEST_DATABASE_URL)
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = maker()
    try:
        seed(db)
        from app.modules.catalog.seed import seed_catalog

        seed_catalog(db, hydrate_cache=True)
        user_with_role(
            db,
            email="e2e.admin@example.com",
            password="E2eAdminPass123!",
            full_name="Admin E2E",
            role_name="admin",
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, trans) -> None:  # type: ignore[no-untyped-def]
        nonlocal nested
        if trans.nested and not nested.is_active:
            nested = connection.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _override_session(db: Session) -> Generator[None, None, None]:
    def _get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> Generator[None, None, None]:
    reset_rate_limit()
    yield
    reset_rate_limit()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    del db
    with TestClient(app) as c:
        probe = c.get("/ingresar")
        token = probe.cookies.get("csrf_token") or c.cookies.get("csrf_token")
        if token:
            c.headers.update({"X-CSRF-Token": token})
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
    user = user_with_role(
        db,
        email=email,
        password=password,
        full_name=full_name,
        role_name=role_name,
    )
    user.totp_enabled = False
    user.totp_secret_enc = None
    user.totp_backup_hashes = None
    user.failed_login_count = 0
    user.locked_until = None
    user.must_change_password = False
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
        role_name="operador",
    )
    return user, password
