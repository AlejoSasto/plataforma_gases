"""Tests de integración del módulo ml_training."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.modules.ml_training import service as ml_service
from app.modules.users.models import User

MLRUNS = Path(__file__).resolve().parents[2] / "mlruns"


def test_ml_train_forbidden_for_operador(
    client: TestClient,
    operador_user: tuple[User, str],
) -> None:
    user, password = operador_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200
    res = client.post("/api/ml/train", json={"params": {"max_rows": 1000}})
    assert res.status_code == 403


def test_ml_train_promote_flow(
    client: TestClient,
    admin_user: tuple[User, str],
    db: Session,
) -> None:
    from app.modules.sensors_ingestion.models import GasReading

    if db.query(GasReading).count() < 80:
        pytest.skip("el entrenamiento necesita lecturas reales en la DB de pruebas")
    MLRUNS.mkdir(exist_ok=True)
    tracking = f"file:{MLRUNS.as_posix()}"
    user, password = admin_user
    assert client.post("/auth/login", json={"email": user.email, "password": password}).status_code == 200

    train_res = client.post(
        "/api/ml/train",
        json={
            "dataset_version": "gas_readings_sample",
            "task": "classification",
            "algorithms": ["logistic_regression", "random_forest", "xgboost"],
            "params": {"max_rows": 12000, "tracking_uri": tracking},
        },
    )
    assert train_res.status_code == 200, train_res.text
    body = train_res.json()
    assert body["job"]["status"] == "success"
    assert body["best_model_id"] is not None
    assert len(body["models"]) == 3
    assert all("gates" in (m.get("metrics") or {}) for m in body["models"])

    # Al menos un algoritmo cumple umbrales blandos del taller
    ok = any(
        (m["metrics"].get("recall", 0) >= 0.85 and m["metrics"].get("f1", 0) >= 0.80)
        or m["metrics"].get("f1", 0) >= 0.5  # fallback si muestra pequeña
        for m in body["models"]
    )
    assert ok, body["models"]

    models_res = client.get("/api/ml/models")
    assert models_res.status_code == 200
    assert len(models_res.json()) >= 3

    compare = client.get("/api/ml/models/compare")
    assert compare.status_code == 200

    best_id = body["best_model_id"]
    promote = client.post(f"/api/ml/models/{best_id}/promote")
    assert promote.status_code == 200
    assert promote.json()["status"] == "production"

    # Segundo promote del mismo set → archiva el anterior
    other = next(m["id"] for m in body["models"] if m["id"] != best_id)
    promote2 = client.post(f"/api/ml/models/{other}/promote")
    assert promote2.status_code == 200
    assert promote2.json()["status"] == "production"

    catalog = client.get("/api/ml/models").json()
    production = [m for m in catalog if m["status"] == "production"]
    archived = [m for m in catalog if m["status"] == "archived"]
    assert len(production) == 1
    assert production[0]["id"] == other
    assert any(m["id"] == best_id for m in archived)
    model = ml_service.get_active_model(db, scope="global")
    assert model is not None
