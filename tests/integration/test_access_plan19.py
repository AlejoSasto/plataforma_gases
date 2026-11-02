"""Flujos de acceso Plan 19: bloqueo, CSRF, rotación, invitación, TOTP, kiosco."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.modules.sensors_ingestion.models import Sensor, Site
from app.modules.users.models import RefreshToken, User, UserSiteScope
from app.shared.copy import LOGIN_BAD, LOGIN_LOCKED


def _login(client: TestClient, email: str, password: str, **extra):
    return client.post("/auth/login", json={"email": email, "password": password, **extra})


@pytest.mark.plan19
def test_login_page_two_columns(client: TestClient) -> None:
    res = client.get("/ingresar")
    assert res.status_code == 200
    assert "Saber a tiempo qué está pasando con los gases en la mina." in res.text
    assert "Mantener la sesión durante mi turno" in res.text
    assert "¿Olvidaste tu contraseña?" in res.text
    assert "csrf_token" in res.cookies or "csrf_token" in client.cookies
    assert 'method="post"' in res.text
    assert 'action="/ingresar"' in res.text
    assert "/static/js/login.js" in res.text
    assert "document.getElementById(\"login-form\")" not in res.text
    assert 'name="csrf_token" value="' in res.text
    csrf_html = res.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    assert len(csrf_html) > 8
    assert res.headers.get("referrer-policy") == "no-referrer"
    assert "no-store" in (res.headers.get("cache-control") or "")


@pytest.mark.plan19
def test_login_query_strips_password(client: TestClient) -> None:
    res = client.get("/ingresar?email=test.admin%40example.com&password=AdminPass123%21", follow_redirects=False)
    assert res.status_code == 302
    loc = res.headers.get("location", "")
    assert loc.endswith("/ingresar")
    assert "password" not in loc.lower()
    assert "email=" not in loc.lower()


@pytest.mark.plan19
def test_form_login_sets_http_only_cookies(client: TestClient, admin_user: tuple[User, str]) -> None:
    user, password = admin_user
    page = client.get("/ingresar")
    csrf = page.cookies.get("csrf_token") or client.cookies.get("csrf_token")
    res = client.post(
        "/ingresar",
        data={"email": user.email, "password": password, "csrf_token": csrf or ""},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") in ("/", "/mi-cuenta")
    assert "password=" not in (res.headers.get("location") or "")
    jar = {**res.cookies, **client.cookies}
    assert jar.get("access_token") or client.cookies.get("access_token")


@pytest.mark.plan19
def test_bad_login_generic_message(client: TestClient) -> None:
    res = _login(client, "nadie@example.com", "ClaveQueNoExiste12")
    assert res.status_code == 401
    assert res.json()["message"] == LOGIN_BAD


@pytest.mark.plan19
def test_lockout_after_five_failures(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    user, _pwd = admin_user
    try:
        res = None
        for _ in range(5):
            res = _login(client, user.email, "ClaveIncorrecta99")
        assert res is not None
        assert res.status_code == 429
        assert LOGIN_LOCKED in res.json()["message"]
    finally:
        db.refresh(user)
        user.failed_login_count = 0
        user.locked_until = None
        db.add(user)
        db.commit()


@pytest.mark.plan19
def test_csrf_rejects_post_without_header() -> None:
    with TestClient(app) as raw:
        raw.get("/ingresar")
        res = raw.post("/auth/login", json={"email": "a@b.co", "password": "xxxxxxxxxxxx"})
        assert res.status_code == 403
        assert res.json()["error"] == "csrf"


@pytest.mark.plan19
def test_refresh_reuse_revokes_all(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    user, password = admin_user
    first = _login(client, user.email, password)
    assert first.status_code == 200
    old_refresh = first.cookies.get("refresh_token") or client.cookies.get("refresh_token")
    assert old_refresh
    rotated = client.post("/auth/refresh")
    assert rotated.status_code == 200
    client.cookies.set("refresh_token", old_refresh)
    reused = client.post("/auth/refresh")
    assert reused.status_code == 401
    live = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .count()
    )
    assert live == 0


@pytest.mark.plan19
def test_invite_accept_and_outbox(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    admin, password = admin_user
    assert _login(client, admin.email, password).status_code == 200
    roles = {r["name"]: r["id"] for r in client.get("/api/roles").json()}
    email = f"invitada.{uuid.uuid4().hex[:8]}@example.com"
    outbox = Path("storage/outbox")
    before = set(outbox.glob("*.txt")) if outbox.exists() else set()
    inv = client.post(
        "/auth/invitar",
        json={
            "email": email,
            "full_name": "Ana Operadora",
            "role_ids": [roles["operador"]],
            "site_ids": [],
        },
    )
    assert inv.status_code == 200
    token = inv.json().get("token")
    assert token
    after = set(outbox.glob("*.txt")) if outbox.exists() else set()
    assert after - before
    client.post("/auth/logout")
    acc = client.post("/auth/invitar/aceptar", json={"token": token, "password": "UnaClaveLargaSegura!"})
    assert acc.status_code == 200
    assert acc.json()["email"] == email


@pytest.mark.plan19
def test_password_reset_outbox(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    user, _pwd = admin_user
    outbox = Path("storage/outbox")
    before = set(outbox.glob("*.txt")) if outbox.exists() else set()
    res = client.post("/auth/recuperar", json={"email": user.email})
    assert res.status_code == 200
    ghost = client.post("/auth/recuperar", json={"email": "noexiste@example.com"})
    assert ghost.status_code == 200
    assert ghost.json()["message"] == res.json()["message"]
    after = set(outbox.glob("*.txt")) if outbox.exists() else set()
    assert after - before


@pytest.mark.plan19
def test_totp_enable_and_login(client: TestClient, admin_user: tuple[User, str], db: Session) -> None:
    pyotp = pytest.importorskip("pyotp")
    user, password = admin_user
    user.totp_enabled = False
    user.totp_secret_enc = None
    user.totp_backup_hashes = None
    db.add(user)
    db.commit()
    assert _login(client, user.email, password).status_code == 200
    start = client.post("/auth/totp/iniciar")
    assert start.status_code == 200
    secret = start.json()["secret"]
    code = pyotp.TOTP(secret).now()
    en = client.post("/auth/totp/activar", json={"secret": secret, "code": code})
    assert en.status_code == 200
    assert len(en.json()["backup_codes"]) == 8
    client.post("/auth/logout")
    no_code = _login(client, user.email, password)
    assert no_code.status_code == 401
    ok = _login(client, user.email, password, totp_code=pyotp.TOTP(secret).now())
    assert ok.status_code == 200
    db.refresh(user)
    user.totp_enabled = False
    user.totp_secret_enc = None
    user.totp_backup_hashes = None
    db.add(user)
    db.commit()


@pytest.mark.plan19
def test_operator_cannot_see_other_zones(
    client: TestClient, operador_user: tuple[User, str], db: Session
) -> None:
    op, password = operador_user
    a = db.query(Site).filter(Site.name == "Zona Plan19 A").first() or Site(name="Zona Plan19 A")
    b = db.query(Site).filter(Site.name == "Zona Plan19 B").first() or Site(name="Zona Plan19 B")
    if a.id is None:
        db.add(a)
    if b.id is None:
        db.add(b)
    db.flush()
    db.query(UserSiteScope).filter(UserSiteScope.user_id == op.id).delete()
    db.add(UserSiteScope(user_id=op.id, site_id=a.id))
    for code, site in (("P19A", a), ("P19B", b)):
        if db.query(Sensor).filter(Sensor.code == code).first() is None:
            db.add(Sensor(site_id=site.id, code=code, gas_type="CH4", unit="%"))
    db.commit()
    assert _login(client, op.email, password).status_code == 200
    items = client.get("/dashboard/api/semaforo").json()["items"]
    ids = {i.get("site_id") for i in items}
    assert b.id not in ids
    other = client.get(f"/zonas/{b.id}", follow_redirects=False)
    assert other.status_code in (403, 302)


@pytest.mark.plan19
def test_kiosk_sala_and_revocation(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert _login(client, admin.email, password).status_code == 200
    created = client.post("/auth/kioscos", json={"name": "Pantalla sala principal", "site_ids": []})
    assert created.status_code == 200
    token = created.json()["token"]
    device_id = created.json()["id"]
    pair = created.json()["pair_url"]
    client.post("/auth/logout")
    sala = client.get(pair)
    assert sala.status_code == 200
    assert 'data-theme="sala"' in sala.text
    other = client.get("/avisos", follow_redirects=False)
    assert other.status_code in (302, 401, 403)
    assert _login(client, admin.email, password).status_code == 200
    rev = client.post(f"/auth/kioscos/{device_id}/revocar")
    assert rev.status_code == 200
    client.post("/auth/logout")
    blocked = client.get(f"/sala?kiosk={token}", follow_redirects=False)
    assert blocked.status_code in (302, 401, 403)


@pytest.mark.plan19
def test_equipo_and_cuenta_screens(client: TestClient, admin_user: tuple[User, str], operador_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert _login(client, admin.email, password).status_code == 200
    eq = client.get("/equipo")
    assert eq.status_code == 200
    assert "Invitar" in eq.text
    me = client.get("/mi-cuenta")
    assert me.status_code == 200
    assert "Sesiones activas" in me.text
    pan = client.get("/pantallas")
    assert pan.status_code == 200
    client.post("/auth/logout")
    op, op_pass = operador_user
    assert _login(client, op.email, op_pass).status_code == 200
    assert client.get("/equipo").status_code == 403
    assert client.get("/pantallas").status_code == 403
    assert "href=\"/equipo\"" not in client.get("/").text
