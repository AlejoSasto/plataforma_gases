"""Accesibilidad de pantallas clave (Plan 20 F2 etapa 10)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.modules.users.models import User

pytestmark = [pytest.mark.e2e, pytest.mark.plan20]


def test_ingresar_has_lang_and_labels(client: TestClient) -> None:
    res = client.get("/ingresar")
    assert res.status_code == 200
    assert 'lang="es-CO"' in res.text
    assert 'for="email"' in res.text or "Correo" in res.text
    assert "<h1" in res.text or "<h2" in res.text


def test_hoy_has_main_landmark(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    res = client.get("/")
    assert res.status_code == 200
    assert "<main" in res.text
    assert 'lang="es-CO"' in res.text
