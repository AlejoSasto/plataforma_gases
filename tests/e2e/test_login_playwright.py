"""E2E Playwright: /login redirige a /ingresar y el formulario entra (Plan 20)."""

from __future__ import annotations

import pytest

from tests.e2e._helpers import BASE, EMAIL, PASSWORD, app_is_live, login_admin

pytestmark = [pytest.mark.e2e, pytest.mark.plan20]


@pytest.fixture(scope="module")
def browser_page():
    pytest.importorskip("playwright.sync_api")
    if not app_is_live():
        pytest.skip("app no responde en E2E_BASE_URL")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


def test_login_redirects_to_ingresar(browser_page) -> None:
    page = browser_page
    page.goto(f"{BASE}/login", wait_until="networkidle")
    assert "/ingresar" in page.url
    assert "password=" not in page.url
    assert page.get_by_label("Correo").is_visible()
    assert "Ingresar" in page.content()
    assert page.locator(".login").count() == 1


def test_login_query_never_keeps_password(browser_page) -> None:
    page = browser_page
    page.goto(
        f"{BASE}/ingresar?email=test.admin%40example.com&password=AdminPass123%21",
        wait_until="networkidle",
    )
    assert "password=" not in page.url
    assert page.url.endswith("/ingresar") or page.url.endswith("/ingresar/")


def test_login_form_enters_hoy(browser_page) -> None:
    page = browser_page
    login_admin(page, EMAIL, PASSWORD)
    body = page.content()
    assert "Hoy" in body or "Todo normal" in body or "atención" in body
