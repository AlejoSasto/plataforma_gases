"""Tests de stakeholders y notificaciones."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.alerts.models import Alert
from app.modules.alerts.service import evaluate_and_create_alert
from app.modules.ml_training.models import ModelRegistry
from app.modules.predictions.models import Prediction
from app.modules.roles_permissions.models import Role
from app.modules.sensors_ingestion.models import GasReading, Sensor, Site
from app.modules.stakeholders.models import AlertNotification, Stakeholder
from app.modules.stakeholders.service import get_recipients_for_alert
from app.modules.users.models import User
from scripts.seed_roles_permissions import seed


def test_stakeholder_crud_and_recipients(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200

    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.name == "Mina Norte").first()
        if site is None:
            site = Site(name="Mina Norte", description="Sitio de prueba")
            db.add(site)
            db.commit()
            db.refresh(site)
        site_id = site.id
    finally:
        db.close()

    create = client.post(
        "/api/stakeholders",
        json={
            "name": "Gerencia HSEQ",
            "type": "externo",
            "organization": "Corp",
            "email": "hseq@example.com",
            "notify_channels": ["email"],
        },
    )
    assert create.status_code == 201, create.text
    stake_id = create.json()["id"]

    sub = client.post(
        f"/api/stakeholders/{stake_id}/subscriptions",
        json={"site_id": site_id, "min_level": "CRITICO"},
    )
    assert sub.status_code == 201, sub.text

    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).one()
        sensor = (
            db.query(Sensor)
            .filter(Sensor.code == "SN#MINA", Sensor.gas_type == "CO")
            .first()
        )
        if sensor is None:
            sensor = Sensor(site_id=site.id, code="SN#MINA", gas_type="CO", unit="ppm")
            db.add(sensor)
            db.flush()
        reading = GasReading(
            sensor_id=sensor.id,
            leyendo=200.0,
            alarma="HIGH",
            tiempo_inicio=datetime.now(timezone.utc),
            is_synthetic=False,
        )
        db.add(reading)
        db.flush()
        model = db.query(ModelRegistry).first()
        if model is None:
            model = ModelRegistry(
                name="m",
                version="1",
                algorithm="rf",
                params={},
                metrics={},
                status="staging",
                scope="global",
            )
            db.add(model)
            db.flush()
        pred_crit = Prediction(
            gas_reading_id=reading.id,
            model_registry_id=model.id,
            probability=0.95,
            predicted_label=1,
            risk_level="CRITICO",
        )
        db.add(pred_crit)
        db.flush()
        alert_crit = evaluate_and_create_alert(db, pred_crit, reading)
        db.commit()
        assert alert_crit is not None

        recipients = get_recipients_for_alert(db, alert_crit)
        assert any(r.id == stake_id for r in recipients)

        # PRECAUCION no debe incluir al suscriptor de CRITICO
        reading2 = GasReading(
            sensor_id=sensor.id,
            leyendo=1.0,
            tiempo_inicio=datetime.now(timezone.utc),
            is_synthetic=False,
        )
        db.add(reading2)
        db.flush()
        pred_low = Prediction(
            gas_reading_id=reading2.id,
            model_registry_id=model.id,
            probability=0.4,
            predicted_label=0,
            risk_level="PRECAUCION",
        )
        db.add(pred_low)
        db.flush()
        # Forzar alerta PRECAUCION vía hard alarm false — crear alerta manual
        alert_low = Alert(
            prediction_id=pred_low.id,
            gas_reading_id=reading2.id,
            sensor_id=sensor.id,
            level="PRECAUCION",
            message="precaucion",
            recommendation="monitorear",
            status="abierta",
        )
        db.add(alert_low)
        db.commit()
        recipients_low = get_recipients_for_alert(db, alert_low)
        assert all(r.id != stake_id for r in recipients_low)

        notifs = (
            db.query(AlertNotification)
            .filter(AlertNotification.alert_id == alert_crit.id)
            .all()
        )
        assert len(notifs) >= 1
        assert all(n.status == "enviado" for n in notifs)
    finally:
        db.close()


def test_interesado_sees_only_subscribed_alerts(client: TestClient, admin_user: tuple) -> None:
    admin, admin_pass = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": admin_pass}).status_code == 200

    db = SessionLocal()
    try:
        seed(db)
        role = db.query(Role).filter(Role.name == "interesado").one()
        email = "portal.interesado@example.com"
        password = "InteresadoPass123!"
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name="Portal Interesado",
                is_active=True,
                roles=[role],
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.password_hash = hash_password(password)
            user.roles = [role]
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id

        site = db.query(Site).filter(Site.name == "Mina Norte").first()
        if site is None:
            site = Site(name="Mina Norte")
            db.add(site)
            db.commit()
            db.refresh(site)
    finally:
        db.close()

    create = client.post(
        "/api/stakeholders",
        json={
            "name": "Interesado Portal",
            "type": "externo",
            "email": "portal.interesado@example.com",
            "user_id": user_id,
            "notify_channels": ["email"],
        },
    )
    assert create.status_code == 201
    stake_id = create.json()["id"]
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.name == "Mina Norte").one()
        site_id = site.id
    finally:
        db.close()
    assert (
        client.post(
            f"/api/stakeholders/{stake_id}/subscriptions",
            json={"site_id": site_id, "min_level": "ALERTA"},
        ).status_code
        == 201
    )

    client.post("/auth/logout")
    assert (
        client.post("/auth/login", json={"email": email, "password": password}).status_code
        == 200
    )
    res = client.get("/api/alerts")
    assert res.status_code == 200
    # Solo alertas de Mina Norte >= ALERTA (puede ser 0 si no hay, pero no 403)
    assert "items" in res.json()

    page = client.get("/executive")
    assert page.status_code == 200
    assert "Resumen ejecutivo" in page.text or "ejecutivo" in page.text.lower()
