"""Verificador de lenguaje natural sobre HTML renderizado (Plan 20 F5)."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.modules.users.models import User
from ml_core.forecasting.explain.language import forbidden_in

pytestmark = pytest.mark.plan20

SKIP_PREFIXES = ("/laboratorio", "/datos/calidad", "/_componentes")
OPERATIVE = (
    "/",
    "/avisos",
    "/zonas",
    "/historial",
    "/ingresar",
    "/mi-cuenta",
    "/sala",
)


def _visible(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


@pytest.mark.parametrize("path", OPERATIVE)
def test_operative_html_plain_language(client: TestClient, operador_user: tuple[User, str], path: str) -> None:
    user, password = operador_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    if any(path.startswith(p) for p in SKIP_PREFIXES):
        pytest.skip("ruta técnica")
    res = client.get(path)
    assert res.status_code in (200, 302, 401, 403)
    if res.status_code != 200 or "text/html" not in (res.headers.get("content-type") or ""):
        return
    hits = forbidden_in(_visible(res.text))
    assert hits == [], f"{path} operador {hits}"
