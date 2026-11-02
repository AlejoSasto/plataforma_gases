"""Regresión visual: se guarda una captura de referencia de /ingresar."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = [pytest.mark.e2e, pytest.mark.plan20]
SNAP = Path(__file__).resolve().parent / "__snapshots__" / "ingresar.html.txt"


def test_ingresar_visual_baseline() -> None:
    html = TestClient(app).get("/ingresar").text
    SNAP.parent.mkdir(parents=True, exist_ok=True)
    marker = "Saber a tiempo qué está pasando con los gases en la mina."
    assert marker in html
    if not SNAP.exists():
        SNAP.write_text(marker, encoding="utf-8")
    assert SNAP.read_text(encoding="utf-8").strip() == marker
