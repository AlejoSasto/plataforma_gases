"""Tests de dashboard UI y APIs (Planes 07/11/18)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.users.models import User


def test_login_page_has_theme(client: TestClient) -> None:
    res = client.get("/login", follow_redirects=True)
    assert res.status_code == 200
    assert "tokens.css" in res.text
    tokens = client.get("/static/css/tokens.css")
    assert tokens.status_code == 200
    assert "Archivo" in tokens.text
    assert "IBM Plex Mono" in tokens.text
    assert "Vigía" in res.text
    assert "theme.css" not in res.text
    assert "bootstrap" not in res.text.lower()


def test_home_requires_auth(client: TestClient) -> None:
    res = client.get("/", follow_redirects=False)
    assert res.status_code in (302, 401, 403)


def test_operador_sees_semaforo_not_users(
    client: TestClient, operador_user: tuple[User, str]
) -> None:
    user, password = operador_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    home = client.get("/")
    assert home.status_code == 200
    assert "Hoy" in home.text or "sensor" in home.text.lower() or "zona" in home.text.lower()
    assert 'href="/equipo"' not in home.text
    assert 'href="/laboratorio"' not in home.text
    assert 'href="/avisos"' in home.text

    api = client.get("/dashboard/api/semaforo")
    assert api.status_code == 200
    assert "items" in api.json()

    active = client.get("/dashboard/api/alertas-activas")
    assert active.status_code == 200
    assert "items" in active.json()


def test_admin_sidebar_has_admin_links(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    home = client.get("/")
    assert home.status_code == 200
    assert 'href="/equipo"' in home.text
    assert 'href="/contactos"' in home.text
