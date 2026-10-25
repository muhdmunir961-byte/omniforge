"""Browser smoke regression for OmniForge's public, static product showcase.

Runs against an actual local HTTP server + headless Chromium. Verifies user
flows and that we never mistake demo playback for hosted CLI execution.
"""
from __future__ import annotations

import contextlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest
from playwright.sync_api import sync_playwright

PUBLIC = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def site():
    class Quiet(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PUBLIC), **kwargs)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


@pytest.fixture(scope="module")
def local_site():
    with site() as url:
        yield url


def test_desktop_journey_search_step_and_integrity(local_site):
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=1)
        page.on("pageerror", lambda e: errors.append(str(e)))
        response = page.goto(local_site, wait_until="networkidle")
        assert response.status == 200
        assert page.locator(".hero h1").inner_text().startswith("See the work.")
        assert page.locator(".case-item").count() == 9
        assert page.locator("#caseWorkspace .terminal-frame").count() == 1
        assert page.locator(".step-meter .meter-fill").count() == 1

        page.locator('[data-open-case="workflow"]').click()
        assert "Coordinate dependent developer tasks" in page.locator(".case-title").inner_text()
        assert "?demo=workflow" in page.url
        page.locator("#nextStep").click()
        assert "STEP 2 OF 4" in page.locator(".meter-copy").inner_text()

        page.keyboard.press("/")
        assert page.locator("#caseSearch").evaluate("(el) => document.activeElement === el")
        page.locator("#caseSearch").fill("provenance")
        assert 1 <= page.locator(".case-item").count() < 9
        page.locator("#caseSearch").fill("definitely_not_a_real_skill_identifier_917271")
        assert page.locator(".case-item").count() == 0
        assert page.locator(".no-results").count() == 1
        page.locator("#clearCaseSearch").click()
        assert page.locator(".case-item").count() == 9

        page.locator("#takeBaseline").click()
        assert page.locator("#labStatus").inner_text() == "MATCH"
        original = page.locator("#hashInput").input_value()
        page.locator("#editSample").click()
        assert page.locator("#hashInput").input_value() != original
        assert page.locator("#labStatus").inner_text() == "MODIFIED"
        page.locator("#resetSample").click()
        assert page.locator("#hashInput").input_value() == original
        assert page.locator("#labStatus").inner_text() == "MATCH"
        assert not errors, errors
        browser.close()


def test_mobile_navigation_focus_and_zero_horizontal_overflow(local_site):
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844},
                                is_mobile=True, has_touch=True)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(local_site, wait_until="networkidle")
        assert page.locator("#menuToggle").is_visible()
        page.locator("#menuToggle").click()
        assert page.locator("#menuToggle").get_attribute("aria-expanded") == "true"
        assert page.locator(".site-head nav").is_visible()
        page.locator('.site-head nav a[href="#live-lab"]').click()
        assert page.locator("#menuToggle").get_attribute("aria-expanded") == "false"
        page.locator("#caseSearch").fill("workflow")
        assert page.locator(".case-item").count() > 0
        page.locator("#caseSearch").fill("")
        assert page.locator(".case-item").count() == 9
        horizontal = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert horizontal <= 2, f"Horizontal overflow {horizontal}px"
        assert not errors, errors
        browser.close()


def test_deeplink_and_no_remote_backend_claim(local_site):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(local_site + "/?demo=install", wait_until="networkidle")
        assert "Install a skill" in page.locator(".case-title").inner_text()
        disclosure = page.locator(".integrity-disclosure").inner_text().lower()
        assert "no python process" in disclosure
        assert page.locator(".proof-grid a").count() >= 3
        browser.close()
