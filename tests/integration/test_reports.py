"""Tests de generación y descarga de reportes."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.modules.ml_training.models import ModelRegistry
from app.modules.users.models import User


def test_reports_alertas_ejecutivo_and_download(
    client: TestClient, admin_user: tuple[User, str]
) -> None:
    admin, password = admin_user
    assert (
        client.post("/auth/login", json={"email": admin.email, "password": password}).status_code
        == 200
    )

    end = date.today()
    start = end - timedelta(days=30)

    alertas = client.post(
        "/api/reports/alertas",
        json={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert alertas.status_code == 200, alertas.text
    body = alertas.json()
    assert body["report"]["type"] == "alertas_periodo"
    rid = body["report"]["id"]
    path = Path(body["report"]["file_path"])
    assert path.is_file()
    assert path.read_bytes()[:4] == b"%PDF"

    dl = client.get(f"/api/reports/{rid}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/pdf")
    assert dl.content[:4] == b"%PDF"

    ejecutivo = client.post(
        "/api/reports/ejecutivo",
        json={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert ejecutivo.status_code == 200, ejecutivo.text
    ebody = ejecutivo.json()
    assert ebody["report"]["type"] == "resumen_ejecutivo"
    epath = Path(ebody["report"]["file_path"])
    assert epath.is_file()
    assert epath.read_bytes()[:2] == b"PK"  # zip/xlsx

    listed = client.get("/api/reports")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 2

    page = client.get("/reports")
    assert page.status_code == 200
    assert "Generar reporte" in page.text


def test_reports_modelo(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert (
        client.post("/auth/login", json={"email": admin.email, "password": password}).status_code
        == 200
    )
    db = SessionLocal()
    try:
        model = db.query(ModelRegistry).first()
        if model is None:
            model = ModelRegistry(
                name="report-test",
                version="1",
                algorithm="rf",
                params={},
                metrics={"f1": 0.8, "precision": 0.7, "recall": 0.9},
                status="staging",
                scope="global",
            )
            db.add(model)
            db.commit()
            db.refresh(model)
        model_id = model.id
    finally:
        db.close()

    res = client.post(f"/api/reports/modelo/{model_id}")
    assert res.status_code == 200, res.text
    assert res.json()["report"]["type"] == "desempeno_modelo"
    assert Path(res.json()["report"]["file_path"]).is_file()


def test_operador_cannot_export_reports(
    client: TestClient, operador_user: tuple[User, str]
) -> None:
    user, password = operador_user
    assert (
        client.post("/auth/login", json={"email": user.email, "password": password}).status_code
        == 200
    )
    end = date.today()
    start = end - timedelta(days=7)
    res = client.post(
        "/api/reports/alertas",
        json={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert res.status_code == 403
