"""Rutas en español, catálogo de componentes y sala (Plan 18)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.modules.users.models import User

REDIRECTS = {
    "/alerts": "/avisos",
    "/sites": "/zonas",
    "/ingestion": "/datos/cargar",
    "/executive": "/resumen",
    "/reports": "/informes",
    "/users": "/equipo",
    "/stakeholders": "/contactos",
    "/audit": "/bitacora",
    "/profile": "/mi-cuenta",
    "/ml/models": "/laboratorio",
    "/login": "/ingresar",
}


@pytest.mark.plan18
def test_old_routes_redirect(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    for old, new in REDIRECTS.items():
        res = client.get(old, follow_redirects=False)
        assert res.status_code in (301, 302), old
        assert new in (res.headers.get("location") or "")


@pytest.mark.plan18
def test_spanish_screens_ok(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    for path in (
        "/",
        "/avisos",
        "/zonas",
        "/historial",
        "/informes",
        "/confiabilidad",
        "/resumen",
        "/equipo",
        "/contactos",
        "/bitacora",
        "/mi-cuenta",
        "/datos/cargar",
        "/datos/calidad",
        "/ajustes/limites",
        "/laboratorio",
        "/sala",
        "/_componentes",
        "/ingresar",
    ):
        res = client.get(path)
        assert res.status_code == 200, f"{path} -> {res.status_code}"
        assert "bootstrap" not in res.text.lower()
        assert "tokens.css" in res.text
        assert "fonts.googleapis" not in res.text
        assert "cdnjs" not in res.text
        assert "unpkg.com" not in res.text


@pytest.mark.plan18
def test_sala_uses_dark_theme(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    res = client.get("/sala")
    assert res.status_code == 200
    assert 'data-theme="sala"' in res.text


@pytest.mark.plan18
def test_component_catalog_has_macros(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    res = client.get("/_componentes")
    assert res.status_code == 200
    assert "Normal" in res.text
    assert "Actuar ya" in res.text
    assert "Evacuar" in res.text


@pytest.mark.plan18
def test_pages_have_lang_and_focus_tokens(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    home = client.get("/")
    assert 'lang="es-CO"' in home.text
    css = client.get("/static/css/base.css")
    assert css.status_code == 200
    assert ":focus-visible" in css.text
    tokens = client.get("/static/css/tokens.css")
    assert tokens.status_code == 200
    assert "Archivo" in tokens.text
    assert "IBM Plex Mono" in tokens.text
