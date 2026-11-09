"""Pantallas del Plan 25 contra la base de pruebas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.modules.sensors_ingestion.instruments import ensure_instrument
from app.modules.sensors_ingestion.models import Sensor, Site
from app.modules.users.models import User, UserInstrumentScope

pytestmark = pytest.mark.plan25


def _login(client: TestClient, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_platform_screens_render(client: TestClient, admin_user: tuple[User, str]) -> None:
    user, password = admin_user
    assert _login(client, user.email, password).status_code == 200
    for path in (
        "/equipos",
        "/zonas",
        "/ajustes/limites",
        "/datos/calidad",
        "/laboratorio/resultados",
        "/laboratorio/por-que-gano",
        "/turno",
        "/avisos",
    ):
        res = client.get(path)
        assert res.status_code == 200, path
        assert "Art. 38" in res.text or path != "/ajustes/limites"


def test_operator_sees_only_scoped_instrument(
    client: TestClient, operador_user: tuple[User, str], db
) -> None:
    user, password = operador_user
    site = Site(name="Sitio alcance plan25")
    db.add(site)
    db.flush()
    mine = ensure_instrument(db, "SERIE-MIA")
    other = ensure_instrument(db, "SERIE-OTRA")
    db.add(Sensor(site_id=site.id, code="SERIE-MIA", gas_type="CH4", unit="%", instrument_id=mine.id))
    db.add(Sensor(site_id=site.id, code="SERIE-OTRA", gas_type="CO", unit="ppm", instrument_id=other.id))
    db.add(UserInstrumentScope(user_id=user.id, instrument_id=mine.id))
    db.commit()
    assert _login(client, user.email, password).status_code == 200
    page = client.get("/equipos")
    assert page.status_code == 200
    assert "SERIE-MIA" in page.text
    assert "SERIE-OTRA" not in page.text
