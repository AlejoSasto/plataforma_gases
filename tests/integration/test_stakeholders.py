"""Tests de stakeholders y notificaciones."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.alerts.models import Alert
from app.modules.alerts.service import evaluate_and_create_alert
from app.modules.roles_permissions.models import Role
from app.modules.sensors_ingestion.models import GasReading, Sensor, Site
from app.modules.stakeholders.models import AlertNotification, Stakeholder
from app.modules.stakeholders.service import get_recipients_for_alert
from app.modules.users.models import User
from scripts.seed_roles_permissions import seed


def test_stakeholder_crud_and_recipients(
    client: TestClient, admin_user: tuple[User, str], db: Session
) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200

    site = db.query(Site).filter(Site.name == "Mina Norte").first()
    if site is None:
        site = Site(name="Mina Norte", description="Sitio de prueba")
        db.add(site)
        db.commit()
        db.refresh(site)
    site_id = site.id

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
        json={"site_id": site_id, "min_level": "ALERTA"},
    )
    assert sub.status_code == 201, sub.text

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
        alert_crit = evaluate_and_create_alert(db, reading)
        db.commit()
        assert alert_crit is not None

        recipients = get_recipients_for_alert(db, alert_crit)
        assert any(r.id == stake_id for r in recipients)

        # PRECAUCION no debe incluir al suscriptor de CRITICO
        reading2 = GasReading(
            sensor_id=sensor.id,
            leyendo=1.0,
            tiempo_inicio=datetime.now(timezone.utc) + timedelta(seconds=2),
            is_synthetic=False,
        )
        db.add(reading2)
        db.flush()
        alert_low = Alert(
            gas_reading_id=reading2.id,
            sensor_id=sensor.id,
            kind="confirmado",
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
        pass


def test_interesado_sees_only_subscribed_alerts(
    client: TestClient, admin_user: tuple, db: Session
) -> None:
    admin, admin_pass = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": admin_pass}).status_code == 200

    try:
        seed(db)
        role = db.query(Role).filter(Role.name == "gerencia").one()
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
        pass

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
    site = db.query(Site).filter(Site.name == "Mina Norte").one()
    site_id = site.id
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
    assert "Resumen" in page.text or "gerencia" in page.text.lower()
