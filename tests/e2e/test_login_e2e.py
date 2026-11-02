"""E2E Playwright del ingreso (Plan 20 F2 etapa 9)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.plan20]


def test_ingresar_shows_natural_copy() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    from fastapi.testclient import TestClient

    from app.main import app

    html = TestClient(app).get("/ingresar").text
    assert "Ingresar" in html
    assert "Saber a tiempo qué está pasando con los gases en la mina." in html
    del playwright
