"""Tests de integración del módulo ml_training (zoo forecasting, Plan 23 F5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.models import User


def test_ml_train_forbidden_for_operador(
    client: TestClient,
    operador_user: tuple[User, str],
) -> None:
    user, password = operador_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    res = client.post("/api/ml/train", json={"algorithms": ["persistencia"]})
    assert res.status_code == 403


def test_ml_train_rejects_legacy_task(
    client: TestClient,
    admin_user: tuple[User, str],
) -> None:
    user, password = admin_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    res = client.post(
        "/api/ml/train",
        json={"task": "classification", "algorithms": ["persistencia"]},
    )
    # schema solo acepta forecast → 422
    assert res.status_code == 422


@pytest.mark.plan23
def test_ml_train_promote_forecast_baselines(
    client: TestClient,
    admin_user: tuple[User, str],
    db: Session,
) -> None:
    from app.modules.sensors_ingestion.models import GasReading

    if db.query(GasReading).count() < 80:
        pytest.skip("el entrenamiento necesita lecturas reales en la DB de pruebas")
    user, password = admin_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200

    train_res = client.post(
        "/api/ml/train",
        json={
            "dataset_version": "gas_readings_sample",
            "task": "forecast",
            "algorithms": ["persistencia", "ets"],
            "params": {"max_rows": 2000},
        },
    )
    assert train_res.status_code == 200, train_res.text
    body = train_res.json()
    assert body["job"]["status"] == "success"
    assert body["best_model_id"] is not None
    assert len(body["models"]) == 2
    assert all(m["algorithm"] in {"persistencia", "ets"} for m in body["models"])

    best_id = body["best_model_id"]
    promote = client.post(f"/api/ml/models/{best_id}/promote")
    assert promote.status_code == 200
    assert promote.json()["status"] == "production"
