"""Flujo de autenticación extremo a extremo."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.users.models import User


def test_login_me_logout_flow(
    client: TestClient,
    admin_user: tuple[User, str],
) -> None:
    user, password = admin_user

    login_res = client.post(
        "/auth/login",
        json={"email": user.email, "password": password},
    )
    assert login_res.status_code == 200
    body = login_res.json()
    assert body["email"] == user.email
    assert "admin" in body["roles"]
    assert "users.manage" in body["permissions"]
    assert "access_token" in login_res.cookies

    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["id"] == user.id

    logout_res = client.post("/auth/logout")
    assert logout_res.status_code == 200

    me_after = client.get("/auth/me")
    assert me_after.status_code == 401


def test_refresh_issues_new_access_token(
    client: TestClient,
    admin_user: tuple[User, str],
) -> None:
    user, password = admin_user
    client.post("/auth/login", json={"email": user.email, "password": password})
    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 200
    assert refresh_res.json()["email"] == user.email
    me_res = client.get("/auth/me")
    assert me_res.status_code == 200
