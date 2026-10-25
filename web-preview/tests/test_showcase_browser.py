"""Browser smoke regression for the OmniForge showcase and real CLI execution lab.

Runs against an actual local HTTP server + headless Chromium. Verifies user
flows and that we never mistake demo playback for hosted CLI execution.
"""
from __future__ import annotations

import contextlib
import importlib.util
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest
from playwright.sync_api import sync_playwright

PUBLIC = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("omniforge_ui_test_backend", PUBLIC / "api" / "terminal.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


@contextlib.contextmanager
def site():
    class Quiet(SimpleHTTPRequestHandler):
        _json = backend.handler._json

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PUBLIC), **kwargs)

        def do_GET(self):
            if self.path.split("?", 1)[0] == "/api/terminal":
                return backend.handler.do_GET(self)
            return super().do_GET()

        def do_POST(self):
            if self.path.split("?", 1)[0] == "/api/terminal":
                return backend.handler.do_POST(self)
            return self.send_error(404, "Unsupported API route")

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
        assert "strictly allowlisted" in disclosure
        assert page.locator(".proof-grid a").count() >= 3
        browser.close()



def test_real_cli_terminal_runs_installed_python_and_rejects_shell(local_site):
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1300, "height": 850})
        page.on("pageerror", lambda e: errors.append(str(e)))
        response = page.goto(local_site + "/terminal.html", wait_until="networkidle")
        assert response.status == 200
        page.wait_for_function("document.getElementById('cliRuntimeStatus').textContent.includes('READY')", timeout=10000)

        page.locator("#runCli").click()
        page.wait_for_function("document.getElementById('cliExecutionLabel').textContent.includes('EXECUTED')", timeout=12000)
        assert '"name": "OmniForge"' in page.locator("#cliOutput").inner_text()

        page.locator("#commandInput").fill("python -c 'print(42)'")
        page.locator("#runCli").click()
        page.wait_for_function("document.getElementById('cliExecutionLabel').textContent.includes('REJECTED')", timeout=10000)
        assert "public server does not run arbitrary Python" in page.locator("#cliOutput").inner_text()

        page.locator('#cliExamples button[data-command="ofprov tamper-demo"]').click()
        page.locator("#runCli").click()
        page.wait_for_function("document.getElementById('cliExecutionLabel').textContent.includes('TAMPER DETECTED')", timeout=12000)
        assert "tamper" in page.locator("#commandInput").input_value()
        assert "Exit code 1 is expected" in page.locator("#cliOutput").inner_text()
        assert page.locator("#traceSteps .trace-row").count() == 3
        assert page.locator("#pythonTab").is_visible()
        page.locator("#pythonTab").click()
        assert page.locator("#pythonPanel").is_visible()
        assert page.locator("#cliPanel").is_hidden()
        assert page.locator("#pythonInput").input_value().strip().startswith("import hashlib")
        page.locator('[data-python="ast"]').click()
        assert "import ast" in page.locator("#pythonInput").input_value()
        assert not errors, errors
        browser.close()


def test_live_terminal_mobile_layout_no_horizontal_overflow(local_site):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page.goto(local_site + "/terminal.html", wait_until="networkidle")
        assert page.locator("#cliTab").is_visible()
        page.locator("#pythonTab").click()
        assert page.locator("#pythonInput").is_visible()
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert overflow <= 2, f"Terminal mobile horizontal overflow: {overflow}px"
        browser.close()



def test_real_browser_python_wasm_worker_executes_code(local_site):
    """Run the *real pinned Pyodide engine*, not a mocked JS output.

    A failing CDN, worker, or Python interpreter should fail this test rather
    than display a simulated result.
    """
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(local_site + "/terminal.html", wait_until="domcontentloaded")
        page.locator("#pythonTab").click()
        page.locator('[data-python="hello"]').click()
        page.locator("#runPython").click()
        page.wait_for_function(
            "document.getElementById('pyExecutionLabel').textContent.includes('COMPLETED')",
            timeout=85000,
        )
        output = page.locator("#pythonOutput").inner_text()
        assert "Hello from actual Python." in output
        assert "1² = 1" in output
        assert page.locator("#pyVersion").inner_text().startswith("PYTHON 3.12.")
        assert not errors, errors
        browser.close()



def test_mobile_paste_four_commands_runs_four_real_python_processes(local_site):
    """Regression for the screenshot: four commands pasted in ONE line.

    The previous single-line input sent the entire string to one server API
    call and produced REJECTED / ALLOWLIST. The new parser must split it into
    four independent, validated real CLI requests.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(local_site + "/terminal.html", wait_until="networkidle")
        page.wait_for_function(
            "document.getElementById('cliRuntimeStatus').textContent.includes('READY')",
            timeout=10000,
        )
        commands = (
            'omniforge doctor omniforge search "API errors" '
            'ofprov snapshot ofprov tamper-demo'
        )
        page.locator("#commandInput").fill(commands)
        assert "4 commands ready" in page.locator("#batchHint").inner_text()
        page.locator("#runCli").click()
        page.wait_for_function(
            "document.getElementById('cliExecutionLabel').textContent.includes('4/4 EXECUTED')",
            timeout=30000,
        )
        result = page.locator("#cliOutput").inner_text()
        assert result.count("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━") >= 5
        for command in (
            "omniforge doctor",
            'omniforge search "API errors"',
            "ofprov snapshot",
            "ofprov tamper-demo",
        ):
            assert command in result
        assert "TAMPERING DETECTED" in result
        assert "Exit code 1 is expected" in result
        assert "4/4 commands returned" in result
        assert "Each command had its own temporary project" in result
        assert page.locator("#stopCli").is_hidden()
        assert not errors, errors
        browser.close()


def test_batch_button_and_multiline_keyboard_input(local_site):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(local_site + "/terminal.html", wait_until="domcontentloaded")
        page.locator("#loadFullDemo").click()
        editor = page.locator("#commandInput")
        assert editor.input_value().splitlines() == [
            "omniforge doctor",
            'omniforge search "API errors"',
            "ofprov snapshot",
            "ofprov tamper-demo",
        ]
        assert "4-command demo loaded" in page.locator("#batchHint").inner_text()
        editor.fill("omniforge doctor")
        editor.press("End")
        editor.press("Enter")
        assert editor.input_value() == "omniforge doctor\n"
        editor.fill("omniforge doctor; rm -rf /")
        assert page.locator("#batchHint").get_attribute("class").endswith("invalid")
        page.locator("#runCli").click()
        assert "INPUT ERROR" in page.locator("#cliOutput").inner_text()
        assert page.locator("#cliExecutionLabel").inner_text() == "INPUT FORMAT ERROR"
        browser.close()
