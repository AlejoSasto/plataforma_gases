"""Tests de integración de alertas y predicciones."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.alerts.models import Alert
from app.modules.alerts.service import acknowledge_alert, evaluate_and_create_alert, resolve_alert
from app.modules.roles_permissions.models import Role
from app.modules.sensors_ingestion.models import GasReading, Sensor, Site
from app.modules.users.models import User
from scripts.seed_roles_permissions import seed

MLRUNS = Path(__file__).resolve().parents[2] / "mlruns"


def _ensure_role_user(db, email: str, password: str, role_name: str) -> User:
    seed(db)
    role = db.query(Role).filter(Role.name == role_name).one()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=role_name,
            is_active=True,
            roles=[role],
        )
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.roles = [role]
        user.is_active = True
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_interesado_cannot_resolve_alert(
    client: TestClient,
    db: Session,
) -> None:
    try:
        interesado = _ensure_role_user(
            db, "test.interesado@example.com", "InteresadoPass123!", "gerencia"
        )
        site = db.query(Site).first()
        if site is None:
            site = Site(name="SITE_TEST_ALERT")
            db.add(site)
            db.flush()
        sensor = (
            db.query(Sensor).filter(Sensor.code == "TEST#ALERT").first()
            or Sensor(site_id=site.id, code="TEST#ALERT", gas_type="CO", unit="ppm")
        )
        if sensor.id is None:
            db.add(sensor)
            db.flush()
        reading = GasReading(
            sensor_id=sensor.id,
            leyendo=100.0,
            unidad="ppm",
            alarma="HIGH",
            tiempo_inicio=datetime.now(timezone.utc),
            is_synthetic=False,
        )
        db.add(reading)
        db.flush()
        alert = evaluate_and_create_alert(db, reading)
        db.commit()
        assert alert is not None
        alert_id = alert.id
    finally:
        pass

    assert (
        client.post(
            "/auth/login",
            json={"email": "test.interesado@example.com", "password": "InteresadoPass123!"},
        ).status_code
        == 200
    )
    view = client.get("/api/alerts")
    assert view.status_code == 200
    resolve = client.post(f"/api/alerts/{alert_id}/resolve", json={})
    assert resolve.status_code == 403


def test_alert_lifecycle_and_audit(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    admin, password = admin_user
    try:
        site = db.query(Site).first() or Site(name="SITE_LIFE")
        if site.id is None:
            db.add(site)
            db.flush()
        sensor = (
            db.query(Sensor)
            .filter(Sensor.code == "LIFE#CO", Sensor.gas_type == "CO")
            .first()
        )
        if sensor is None:
            sensor = Sensor(site_id=site.id, code="LIFE#CO", gas_type="CO", unit="ppm")
            db.add(sensor)
            db.flush()
        reading = GasReading(
            sensor_id=sensor.id,
            leyendo=50.0,
            unidad="ppm",
            alarma="ALARMA",
            tiempo_inicio=datetime.now(timezone.utc),
            is_synthetic=False,
        )
        db.add(reading)
        db.flush()
        alert = evaluate_and_create_alert(db, reading)
        db.commit()
        assert alert is not None
        alert_id = alert.id

        acknowledge_alert(db, alert_id, admin)
        resolve_alert(db, alert_id, admin, "ok")
        refreshed = db.query(Alert).filter(Alert.id == alert_id).one()
        assert refreshed.status == "resuelta"
        assert refreshed.acknowledged_by == admin.id
        assert refreshed.resolved_at is not None
    finally:
        pass

    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    listed = client.get("/api/alerts", params={"status": "resuelta"})
    assert listed.status_code == 200


def test_forecasts_filter_by_sensor(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    res = client.get("/api/forecasts", params={"sensor_id": 1})
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "total" in body
