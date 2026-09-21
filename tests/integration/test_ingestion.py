"""Tests de integración de ingesta ETL."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.modules.users.models import User

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@pytest.fixture()
def sample_excel() -> Path:
    path = next(RAW_DIR.glob("dls_report_*.xlsx"), None)
    if path is None:
        pytest.skip("No hay archivos dls_report en data/raw")
    return path


def test_ingestion_forbidden_for_operador(
    client: TestClient,
    operador_user: tuple[User, str],
    sample_excel: Path,
) -> None:
    user, password = operador_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    with sample_excel.open("rb") as fh:
        res = client.post(
            "/api/ingestion/upload",
            files={"files": (sample_excel.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert res.status_code == 403


def test_ingestion_upload_as_admin(
    client: TestClient,
    admin_user: tuple[User, str],
    sample_excel: Path,
) -> None:
    user, password = admin_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    with sample_excel.open("rb") as fh:
        res = client.post(
            "/api/ingestion/upload",
            files={"files": (sample_excel.name, fh, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] in {"success", "failed"}
    assert body["rows_ingested"] > 0
    assert "transforms" in body["log"]
    assert body["log"]["rows_clean"] > 0

    runs = client.get("/api/ingestion/runs")
    assert runs.status_code == 200
    assert runs.json()["total"] >= 1

    detail = client.get(f"/api/ingestion/runs/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == body["id"]
