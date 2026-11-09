"""Tests de generación y descarga de reportes."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

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
    raw = path.read_bytes()
    assert raw[:4] == b"%PDF"
    assert "Avisos del periodo" in raw.decode("latin-1", errors="ignore")

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
    epdf = epath.read_bytes()
    assert epdf[:4] == b"%PDF"
    assert "Resumen para gerencia" in epdf.decode("latin-1", errors="ignore")

    excel = client.post(
        "/api/reports/ejecutivo",
        json={"start": start.isoformat(), "end": end.isoformat(), "formato": "xlsx"},
    )
    assert excel.status_code == 200, excel.text
    assert Path(excel.json()["report"]["file_path"]).read_bytes()[:2] == b"PK"

    confiabilidad = client.post("/api/reports/confiabilidad")
    assert confiabilidad.status_code == 200, confiabilidad.text
    cpath = Path(confiabilidad.json()["report"]["file_path"])
    cblob = cpath.read_bytes()
    assert cblob[:4] == b"%PDF"
    assert "Confiabilidad" in cblob.decode("latin-1", errors="ignore")

    listed = client.get("/api/reports")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 2

    page = client.get("/reports")
    assert page.status_code == 200
    assert "Generar y descargar" in page.text or "Informes" in page.text


def test_reports_modelo(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    admin, password = admin_user
    assert (
        client.post("/auth/login", json={"email": admin.email, "password": password}).status_code
        == 200
    )
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
