"""Ensayo técnico de las 5 tareas de aceptación (Plan 20 F6).

No sustituye las 3–5 sesiones en mina ni el SUS con personas reales.
"""

from __future__ import annotations

import pytest

from tests.e2e._helpers import BASE, app_is_live, login_admin

pytestmark = [pytest.mark.e2e, pytest.mark.plan20]


@pytest.fixture(scope="module")
def page():
    pytest.importorskip("playwright.sync_api")
    if not app_is_live():
        pytest.skip("app no responde en E2E_BASE_URL")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        login_admin(pg)
        yield pg
        browser.close()


def test_t1_banner_hoy(page) -> None:
    page.goto(f"{BASE}/", wait_until="networkidle")
    body = page.locator("body").inner_text()
    assert "Hoy" in body
    assert any(token in body for token in ("Todo normal", "atención", "zonas"))


def test_t2_zona_y_por_que(page) -> None:
    page.goto(f"{BASE}/avisos", wait_until="networkidle")
    body = page.locator("body").inner_text()
    assert "Avisos" in body
    assert any(token in body for token in ("Por qué", "por qué", "Evacuar", "Actuar", "Vigilar", "abierto"))


def test_t3_ya_lo_vi_si_hay_aviso(page) -> None:
    page.goto(f"{BASE}/avisos", wait_until="networkidle")
    btn = page.get_by_role("button", name="Ya lo vi")
    if btn.count() == 0:
        pytest.skip("no hay avisos abiertos para acusar")
    btn.first.click()
    page.wait_for_timeout(1200)
    assert "aviso" in page.locator("body").inner_text().lower()


def test_t4_confiabilidad_frase(page) -> None:
    page.goto(f"{BASE}/confiabilidad", wait_until="networkidle")
    body = page.locator("body").inner_text().lower()
    assert any(
        token in body
        for token in ("confiabilidad", "acierto", "a tiempo", "anticipación", "situaciones")
    )


def test_t5_informes_generar(page) -> None:
    page.goto(f"{BASE}/informes", wait_until="networkidle")
    body = page.locator("body").inner_text()
    assert "Generar y descargar" in body
    data = page.evaluate(
        """async () => {
          return await PG.api("/api/reports/alertas", {
            method: "POST",
            body: { start: "2026-10-01", end: "2026-11-01" },
          });
        }"""
    )
    url = (data.get("report") or {}).get("download_url")
    assert url and "/api/reports/" in url
