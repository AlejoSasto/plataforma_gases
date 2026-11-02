"""E2E: las pantallas con gráfico dibujan serie o estado vacío explicativo (Plan 23 F7)."""

from __future__ import annotations

import pytest

from tests.e2e._helpers import BASE, EMAIL, PASSWORD, app_is_live, login_admin

pytestmark = [pytest.mark.e2e, pytest.mark.plan23]


PAGES = [
    "/",
    "/historial",
    "/confiabilidad",
]


@pytest.fixture(scope="module")
def browser_page():
    pytest.importorskip("playwright.sync_api")
    if not app_is_live():
        pytest.skip("app no responde en E2E_BASE_URL")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors: list[str] = []

        def on_console(msg) -> None:
            if msg.type == "error":
                errors.append(msg.text)

        def on_page_error(exc) -> None:
            errors.append(str(exc))

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page._pg_errors = errors  # type: ignore[attr-defined]
        yield page
        browser.close()


def _assert_charts(page) -> None:
    charts = page.locator("[data-chart]")
    n = charts.count()
    if n == 0:
        return
    for i in range(n):
        el = charts.nth(i)
        el.wait_for(state="visible", timeout=15000)
        # Serie SVG con path, o mensaje vacío explicativo
        has_path = el.locator("svg path").count() > 0
        empty_text = el.inner_text()
        has_empty = (
            "no tiene lecturas" in empty_text.lower()
            or "no pudimos cargar" in empty_text.lower()
            or "aún no hay" in empty_text.lower()
        )
        assert has_path or has_empty, f"gráfico {i} sin serie ni estado vacío: {empty_text[:120]!r}"


def test_charts_render_after_login(browser_page) -> None:
    page = browser_page
    login_admin(page, EMAIL, PASSWORD)
    for path in PAGES:
        page.goto(f"{BASE}{path}", wait_until="networkidle")
        page.wait_for_timeout(800)
        _assert_charts(page)
    # Cero errores de consola (incluye CSP)
    errs = [e for e in page._pg_errors if "favicon" not in e.lower()]  # type: ignore[attr-defined]
    assert not errs, f"errores de consola: {errs}"


def test_sensor_detail_chart(browser_page) -> None:
    page = browser_page
    login_admin(page, EMAIL, PASSWORD)
    # Sensor con datos reales densos en DEV (si existe); si no, /sensores/47 suele ser H2S
    page.goto(f"{BASE}/sensores/47", wait_until="networkidle")
    page.wait_for_timeout(800)
    if page.locator("[data-chart]").count() == 0:
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.wait_for_timeout(500)
    _assert_charts(page)
    body = page.content()
    assert "Datos hasta el" in body or "Ahora y lo que viene" in body
