"""Real execution tests for the PUBLIC restricted OmniForge terminal endpoint."""
from __future__ import annotations

import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

MODULE = Path(__file__).resolve().parents[1] / "api" / "terminal.py"
spec = importlib.util.spec_from_file_location("omniforge_public_terminal", MODULE)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


@pytest.mark.parametrize("command", [
    "python -c 'print(1)'",
    "python -m os",
    "python /etc/passwd",
    "bash -c whoami",
    "rm -rf /",
    "curl https://example.com",
    "omniforge run python-symbols --approve",
    "omniforge browser --url http://example.com",
    "omniforge code --task x",
    "omniforge manifest --out /tmp/file",
    "omniforge install log-triage --project /home",
    "ofprov verify --project /etc",
    "ofprov anchor",
    "ofprov backup",
    'omniforge search "--allow-network"',
    "omniforge doctor; whoami",
    "omniforge doctor\nomniforge run secret-hygiene",
    "omniforge load ../secrets",
    "omniforge budget --selected /etc/passwd",
    "python --version; python -c secret",
])
def test_public_endpoint_rejects_unsafe_commands(command):
    with pytest.raises(api.DemoError):
        api._parse(command)


@pytest.mark.parametrize("command", [
    "python --version",
    "omniforge doctor",
    "oforge --version",
    "omniforge list",
    'omniforge search "API errors"',
    'omniforge related "python errors"',
    'omniforge plan "debug python errors"',
    "omniforge budget --selected log-triage",
    "omniforge load python-symbols",
    "omniforge inspect",
    "omniforge catalog python",
    "ofprov init",
    "ofprov snapshot",
    "ofprov verify",
    "ofprov audit",
    "ofprov proof",
    "ofprov tamper-demo",
])
def test_strict_allowlist_accepts_safe_commands(command):
    args,kind = api._parse(command)
    assert kind in {"cli", "inspect", "provenance", "python"}
    assert args


def test_live_python_real_output_and_version():
    output = api.execute("python --version")
    assert output["ok"] is True
    assert output["exit_code"] == 0
    assert "Python 3." in output["stdout"] or "Python 3." in output["stderr"]
    assert output["mode"] == "server-python-actual-cli"


def test_live_omniforge_doctor_is_real_installed_package():
    output = api.execute("omniforge doctor")
    assert output["ok"] is True, output
    result = json.loads(output["stdout"])
    assert result["name"] == "OmniForge"
    assert len(result["skills"]) == 18
    assert result["version"] == "1.3.1"


def test_live_search_returns_relevant_real_skill():
    output = api.execute('omniforge search "API errors"')
    assert output["ok"] is True, output
    assert "log-triage" in output["stdout"]


def test_ephemeral_provenance_and_tamper_detection():
    snap = api.execute("ofprov snapshot")
    assert snap["ok"] is True, snap
    assert snap["steps"][0]["command"] == "ofprov init"
    assert json.loads(snap["stdout"])["entry_hash"]
    verify = api.execute("ofprov verify")
    assert verify["ok"] is True, verify
    assert json.loads(verify["stdout"])["ok"] is True
    changed = api.execute("ofprov tamper-demo")
    assert changed["ok"] is False, changed
    assert changed["exit_code"] == 1
    assert "modified" in changed["stdout"].lower() or "mismatch" in changed["stdout"].lower() or "changed" in changed["stdout"].lower()
    assert changed["steps"][2]["status"] == "fixture-change"


def test_every_request_uses_fresh_non_persistent_project():
    first = api.execute("ofprov init")
    second = api.execute("ofprov init")
    assert first["ok"] and second["ok"]
    assert json.loads(first["stdout"])["project_id"] != json.loads(second["stdout"])["project_id"]


def test_http_real_status_json_body_and_same_origin_enforcement():
    class Quiet(api.handler):
        def log_message(self, *_):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}/api/terminal"
        with urlopen(base, timeout=10) as response:
            obj = json.load(response)
            assert obj["ok"] is True
            assert obj["samples"] and "real Python" in obj["engine"]
            assert obj["self_test"] == "PASS"
            assert obj["package_version"] == "1.3.1"
            assert obj["package_source"] == "bundled-canonical-source"

        payload = json.dumps({"command": "python --version"}).encode()
        request = Request(base, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=10) as response:
            obj = json.load(response)
            assert obj["ok"] is True
            assert "Python" in obj["stdout"]

        denied = Request(base, data=payload, headers={
            "Content-Type": "application/json",
            "Origin": "https://attacker.example",
        }, method="POST")
        with pytest.raises(HTTPError) as exc:
            urlopen(denied, timeout=10)
        assert exc.value.code == 403

        unsafe = Request(base, data=json.dumps({"command": "python -c 'print(1)'"}).encode(),
                         headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(HTTPError) as exc:
            urlopen(unsafe, timeout=10)
        assert exc.value.code == 400
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=2)

 
def test_bundled_runtime_sources_match_canonical_src():
    """Do not silently ship stale / modified OmniForge core to Vercel."""
    repo_root = Path(__file__).resolve().parents[2]
    canonical = repo_root / "src" / "omniforge"
    vendor = repo_root / "web-preview" / "omniforge"
    # Python/pytest generate ephemeral bytecode during tests. Only compare
    # shipped source/assets; never compare runtime __pycache__ files.
    expected = {path.relative_to(canonical): path.read_bytes()
                for path in canonical.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
                and path.suffix != ".pyc"}
    observed = {path.relative_to(vendor): path.read_bytes()
                for path in vendor.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
                and path.suffix != ".pyc"}
    assert len(expected) >= 49
    assert observed == expected, "Bundled web-preview/omniforge drifted from core package"


def test_clean_python_uses_bundled_cli_without_pip_install(tmp_path):
    """Emulate Vercel subprocess: cwd=sample, stripped Python site packages."""
    import os
    import subprocess
    import sys
    import json

    root = Path(__file__).resolve().parents[1]
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PYTHONPATH": str(root),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "LANG": "C.UTF-8",
    }

    def run(*args):
        return subprocess.run(
            [sys.executable, "-S", "-m", *args], cwd=tmp_path, env=env,
            capture_output=True, text=True, timeout=6, check=True
        ).stdout

    doctor = json.loads(run("omniforge.cli", "doctor"))
    assert doctor["version"] == "1.3.1"
    assert len(doctor["skills"]) == 18
    search = run("omniforge.cli", "search", "API errors")
    assert "log-triage" in search

    (tmp_path / "app.py").write_text("value = 42\\n", encoding="utf-8")
    initialized = json.loads(run(
        "omniforge.provenance_v2_cli", "init", "--project", str(tmp_path)
    ))
    assert initialized.get("ok", True) is True
    snapshot = json.loads(run(
        "omniforge.provenance_v2_cli", "snapshot", "--project", str(tmp_path)
    ))
    assert snapshot.get("ok", True) is True
    verified = json.loads(run(
        "omniforge.provenance_v2_cli", "verify", "--project", str(tmp_path),
        "--check-files"
    ))
    assert verified["ok"]
