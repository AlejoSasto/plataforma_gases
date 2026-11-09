"""E2E: las pantallas con gráfico dibujan serie o estado vacío explicativo (Plan 23 F7)."""

from __future__ import annotations

import pytest

from tests.e2e._helpers import BASE, EMAIL, PASSWORD, app_is_live, login_admin

pytestmark = [pytest.mark.e2e, pytest.mark.plan23, pytest.mark.plan25]


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


def _series_points(page) -> int:
    return page.evaluate(
        """() => {
            if (!window.echarts) return 0;
            const nodes = document.querySelectorAll('[data-chart]');
            let total = 0;
            nodes.forEach((el) => {
                const inst = echarts.getInstanceByDom(el);
                if (!inst) return;
                const series = inst.getOption().series || [];
                series.forEach((s) => {
                    const data = s.data || [];
                    total += data.filter((p) => p != null && p !== '-').length;
                });
            });
            return total;
        }"""
    )


def test_sensor_detail_chart(browser_page) -> None:
    page = browser_page
    login_admin(page, EMAIL, PASSWORD)
    page.goto(f"{BASE}/", wait_until="networkidle")
    html = page.content()
    import re

    ids = re.findall(r"/sensores/(\d+)", html)
    assert ids, "no hay un sensor real enlazado en Hoy"
    chosen = None
    for sensor_id in ids:
        res = page.request.get(f"{BASE}/dashboard/api/series/{sensor_id}?hours=2160")
        if not res.ok:
            continue
        body = res.json()
        points = body.get("points") or body.get("series") or []
        if isinstance(points, list) and len(points) > 0:
            chosen = sensor_id
            break
    assert chosen, "ningún sensor real devolvió puntos de serie"
    page.goto(f"{BASE}/sensores/{chosen}", wait_until="networkidle")
    page.wait_for_timeout(800)
    assert _series_points(page) > 0
