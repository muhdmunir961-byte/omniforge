"""True end-to-end integration tests: opt-in in GitHub Actions.

No real external model, user website or secret is contacted.
The local model fixture uses HTTP transport (not a monkeypatch).
"""
from __future__ import annotations

import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from omniforge.autocode import apply_proposal, request_edits
from omniforge.agents import execute_workflow
from omniforge.browser import browser_session
from omniforge.runtime import execute_run, prepare_run

pytestmark = pytest.mark.skipif(
    os.environ.get("OMNIFORGE_LIVE") != "1", reason="run explicitly with OMNIFORGE_LIVE=1"
)


class LocalWeb(BaseHTTPRequestHandler):
    def do_GET(self):
        html = (
            '<!doctype html><html><head><title>OmniForge Local E2E</title></head>'
            '<body><input id="entry" aria-label="entry">'
            '<button id="go" onclick="document.getElementById(\'status\').textContent='
            'document.getElementById(\'entry\').value">Submit</button>'
            '<div id="status">Initial</div></body></html>'
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, *args):
        return


class MockModel(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64_000:
            self.send_error(413)
            return
        payload = json.loads(self.rfile.read(length))
        self.__class__.received.append(payload)
        files = json.loads(payload["messages"][1]["content"])["files"]
        assert [item["path"] for item in files] == ["app.py"]
        assert files[0]["content"] == "answer = 1\n"
        result = {"choices": [{"message": {"content": json.dumps({"edits": [
            {"path": "app.py", "sha256": files[0]["sha256"],
             "content": "answer = 2\n"}
        ]})}}]}
        encoded = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args):
        return


@pytest.fixture
def serve():
    servers = []
    threads = []

    def start(handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)
        return f"http://127.0.0.1:{server.server_port}"
    yield start
    for server in servers:
        server.shutdown()
        server.server_close()
    for thread in threads:
        thread.join(timeout=2)


def test_live_browser_chromium_fill_click_screenshot(tmp_path: Path, serve):
    pytest.importorskip("playwright.sync_api")
    base = serve(LocalWeb)
    result = browser_session(
        base,
        steps=[
            {"action": "fill", "selector": "#entry", "value": "end-to-end confirmed"},
            {"action": "click", "selector": "#go"},
            {"action": "wait", "milliseconds": 80},
            {"action": "screenshot"},
        ],
        project=tmp_path, screenshot="artifacts/browser.png",
        allow_local=True, approve=True
    )
    assert result["status"] == "completed", result
    assert result["title"] == "OmniForge Local E2E"
    assert "end-to-end confirmed" in result["text"]
    screenshot = tmp_path / "artifacts" / "browser.png"
    assert screenshot.is_file() and screenshot.stat().st_size > 1000


def test_live_docker_isolated_skill(tmp_path: Path):
    if not shutil.which("docker"):
        pytest.fail("Docker is required for end-to-end verification")
    target = tmp_path / "sample.py"
    target.write_text("class Example:\n    pass\n", encoding="utf-8")
    plan = prepare_run("python-symbols", [str(target)], tmp_path, docker=True, timeout=90)
    assert plan["mode"] == "docker-isolated"
    assert "--network" in plan["command"] and plan["command"][plan["command"].index("--network")+1] == "none"
    # Preserve file access for private 0700 project roots without granting root privileges.
    assert "--user" in plan["command"]
    assert plan["command"][plan["command"].index("--user")+1] == f"{os.getuid()}:{os.getgid()}"
    response = execute_run(plan, approve=True)
    assert response["status"] == "completed", json.dumps(response, indent=2)
    parsed = json.loads(response["stdout"])
    assert any(x["name"] == "Example" for x in parsed["symbols"]), parsed
    # Code and data were passed to a read-only container mount.
    assert target.read_text(encoding="utf-8") == "class Example:\n    pass\n"


def test_live_http_model_proposal_preview_and_apply(tmp_path: Path, serve):
    MockModel.received.clear()
    endpoint = serve(MockModel) + "/v1/chat/completions"
    file = tmp_path / "app.py"
    file.write_text("answer = 1\n", encoding="utf-8")
    (tmp_path / "secret.env").write_text("VERY_PRIVATE_TEST_VALUE\n")
    proposal = request_edits(
        "set answer to 2", tmp_path, ["app.py"], endpoint=endpoint, model="mock-e2e"
    )
    assert proposal["status"] == "proposal", proposal
    assert len(MockModel.received) == 1
    assert "VERY_PRIVATE_TEST_VALUE" not in json.dumps(MockModel.received)
    preview = apply_proposal(proposal, tmp_path)
    assert preview["status"] == "preview-only"
    assert file.read_text() == "answer = 1\n"
    applied = apply_proposal(proposal, tmp_path, approve=True)
    assert applied["status"] == "applied"
    assert file.read_text() == "answer = 2\n"
    assert (Path(applied["backup"]) / "app.py").read_text() == "answer = 1\n"


def test_live_docker_dependency_workflow(tmp_path: Path):
    sample = tmp_path / "workflow_sample.py"
    sample.write_text("def ready(): return True\n", encoding="utf-8")
    workflow = tmp_path / "workflow.json"
    workflow.write_text(json.dumps({"tasks": [
        {"id": "inspect", "kind": "skill", "skill": "python-symbols",
         "args": [str(sample)]},
        {"id": "confirm", "kind": "skill", "skill": "python-symbols",
         "args": [str(sample)], "depends_on": ["inspect"]}
    ]}))
    preview = execute_workflow(workflow, tmp_path)
    assert preview["success"] and len(preview["tasks"]) == 2
    assert all(step["status"] == "preview-only" for step in preview["tasks"])
    result = execute_workflow(workflow, tmp_path, approve=True, timeout=90)
    assert result["success"], json.dumps(result, indent=2)
    assert [step["id"] for step in result["tasks"]] == ["inspect", "confirm"]
    assert all(step["status"] == "completed" for step in result["tasks"])
    assert all("ready" in step["stdout"] for step in result["tasks"])
