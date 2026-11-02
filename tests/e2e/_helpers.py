"""Utilidades E2E contra la app en Docker (Plan 20)."""

from __future__ import annotations

import os
import urllib.request


BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
EMAIL = os.environ.get("E2E_EMAIL", "test.admin@example.com")
PASSWORD = os.environ.get("E2E_PASSWORD", "AdminPass123!")


def app_is_live() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE}/health", timeout=3) as res:
            return res.status == 200
    except Exception:  # noqa: BLE001
        return False


def login_admin(page, email: str = EMAIL, password: str = PASSWORD) -> None:
    page.goto(f"{BASE}/ingresar", wait_until="networkidle")
    assert "password=" not in page.url
    page.fill("#email", email)
    page.fill("#password", password)
    page.click("#login-form button[type=submit]")
    page.wait_for_function("() => location.pathname === '/' || location.pathname === '/mi-cuenta'", timeout=15000)
    assert "password=" not in page.url
