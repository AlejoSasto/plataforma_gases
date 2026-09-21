"""Tests de autorización RBAC."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.users.models import User


def test_users_manage_forbidden_for_operador(
    client: TestClient,
    operador_user: tuple[User, str],
) -> None:
    user, password = operador_user
    login = client.post("/auth/login", json={"email": user.email, "password": password})
    assert login.status_code == 200

    res = client.get("/api/users")
    assert res.status_code == 403
    assert res.json()["error"] == "permission_denied"


def test_users_manage_allowed_for_admin(
    client: TestClient,
    admin_user: tuple[User, str],
) -> None:
    user, password = admin_user
    login = client.post("/auth/login", json={"email": user.email, "password": password})
    assert login.status_code == 200

    res = client.get("/api/users")
    assert res.status_code == 200
    assert "items" in res.json()


def test_admin_creates_user_and_assigns_role(
    client: TestClient,
    admin_user: tuple[User, str],
    db: Session,
) -> None:
    admin, password = admin_user
    client.post("/auth/login", json={"email": admin.email, "password": password})

    roles_res = client.get("/api/roles")
    assert roles_res.status_code == 200
    roles = {r["name"]: r["id"] for r in roles_res.json()}
    assert "operador_mina" in roles

    email = f"nuevo.operador.{uuid.uuid4().hex[:8]}@example.com"
    create_res = client.post(
        "/api/users",
        json={
            "email": email,
            "password": "NuevoPass123!",
            "full_name": "Nuevo Operador",
            "role_ids": [roles["operador_mina"]],
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["roles"] == ["operador_mina"]
    assert "password" not in created
    assert "password_hash" not in created

    # El nuevo usuario ve sus permisos en /auth/me
    client.post("/auth/logout")
    login2 = client.post(
        "/auth/login",
        json={"email": email, "password": "NuevoPass123!"},
    )
    assert login2.status_code == 200
    me = client.get("/auth/me")
    assert me.status_code == 200
    me_body = me.json()
    assert "operador_mina" in me_body["roles"]
    assert "alerts.view" in me_body["permissions"]
    assert "users.manage" not in me_body["permissions"]

    # Auditoría de login y creación
    actions = {
        a.action
        for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(20).all()
    }
    assert "login" in actions
    assert "user.create" in actions
