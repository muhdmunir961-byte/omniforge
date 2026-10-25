"""OmniForge's PUBLIC demo API: real Python subprocesses, strict command allowlist.

No shell, no caller-selected file paths, no code execution, no network tools,
no env passthrough, and no cross-request state. This service is *not* a Python
sandbox for arbitrary user code; the browser-side WASM worker handles that.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

# Vercel's function bundles the exact canonical package under the site root.
# Missing source must NOT be mistaken for a healthy CLI service.
RUNTIME_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUNTIME_ROOT))
from omniforge import __version__ as BUNDLED_VERSION

MAX_REQUEST_BYTES = 1024
MAX_COMMAND_CHARS = 240
MAX_BATCH_COMMANDS = 4
MAX_OUTPUT_BYTES = 16_000
SUBPROCESS_TIMEOUT_SECONDS = 5
ALLOWED_SKILLS = frozenset({
    "api-probe", "browser-snapshot", "dependency-inventory", "esptool-chip",
    "firmware-preflight", "git-diff-review", "kicad-drc", "log-triage",
    "openapi-inventory", "python-symbols", "repo-recon", "secret-hygiene",
    "sqlite-inspector", "trivy-scan",
})
SAFE_DEMO = "This is a fresh, disposable sample project; nothing is saved between requests."
USAGE = (
    "Allowed: python --version, omniforge --version, omniforge doctor, "
    "omniforge list, omniforge search \"task\", omniforge related \"task\", "
    "omniforge plan \"task\", omniforge budget [--selected SKILL], "
    "omniforge load SKILL, omniforge catalog [query], "
    "omniforge inspect, ofprov init|snapshot|verify|audit|proof|tamper-demo. "
    "For arbitrary Python, use the in-browser Python Playground tab."
)


class DemoError(ValueError):
    pass


def _text_argument(value: str, *, limit: int = 120) -> str:
    if not value or len(value) > limit or any(ord(char) < 32 for char in value):
        raise DemoError("Invalid or excessively long search input.")
    if value.startswith("-"):
        raise DemoError("Search text must not begin with a command option.")
    return value


def _parse(command: str) -> tuple[list[str], str]:
    """Return a fixed argv for genuine installed Python CLI modules.

    Caller input is allowed ONLY as validated search text or a known skill.
    No path, interpreter flag, execution mode, shell, URL, model, token or
    wallet is ever passed to a subprocess.
    """
    if not isinstance(command, str) or len(command) > MAX_COMMAND_CHARS:
        raise DemoError("Command must be plain text, maximum 240 characters.")
    if not command.strip() or any(ord(char) < 32 for char in command):
        raise DemoError("Enter a single, one-line command.")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise DemoError("Incomplete quoting. Close your quotation marks.") from exc
    if not tokens or len(tokens) > 12:
        raise DemoError("Use one supported demo command.")
    name, *args = tokens
    if name == "python":
        if args == ["--version"]:
            return [sys.executable, "--version"], "python"
        raise DemoError("The public server does not run arbitrary Python. Use the browser Python Playground.")
    if name == "ofprov":
        if len(args) != 1 or args[0] not in {
            "init", "snapshot", "verify", "audit", "proof", "tamper-demo",
        }:
            raise DemoError("Supported ofprov demos: init, snapshot, verify, audit, proof, tamper-demo.")
        # ofprov gets *only* a fixed subcommand; the project path is injected
        # later by this handler, never read from a caller.
        return [args[0]], "provenance"
    if name not in ("omniforge", "oforge"):
        raise DemoError("Unknown command. " + USAGE)
    if args in (["doctor"], ["list"], ["--version"]):
        return [sys.executable, "-m", "omniforge.cli", *args], "cli"
    if args == ["inspect"]:
        return [sys.executable, "-m", "omniforge.cli", "inspect"], "inspect"
    if args and args[0] in ("search", "related", "plan"):
        if len(args) != 2:
            raise DemoError("Provide exactly one quoted query, e.g. omniforge search \"API errors\".")
        return [sys.executable, "-m", "omniforge.cli", args[0],
                _text_argument(args[1])], "cli"
    if args and args[0] == "budget":
        if len(args) == 1:
            return [sys.executable, "-m", "omniforge.cli", "budget"], "cli"
        if len(args) == 3 and args[1] == "--selected" and args[2] in ALLOWED_SKILLS:
            return [sys.executable, "-m", "omniforge.cli", "budget", "--selected", args[2]], "cli"
        raise DemoError("Use omniforge budget or omniforge budget --selected SKILL.")
    if args and args[0] == "load":
        if len(args) == 2 and args[1] in ALLOWED_SKILLS:
            return [sys.executable, "-m", "omniforge.cli", "load", args[1]], "cli"
        raise DemoError("Choose a known bundled skill: log-triage, python-symbols, etc.")
    if args and args[0] == "catalog":
        if len(args) == 1:
            return [sys.executable, "-m", "omniforge.cli", "catalog", "--limit", "5"], "cli"
        if len(args) == 2:
            return [sys.executable, "-m", "omniforge.cli", "catalog",
                    _text_argument(args[1], limit=70), "--limit", "5"], "cli"
        raise DemoError("Use omniforge catalog or omniforge catalog \"topic\".")
    raise DemoError("This command is not available on the public server. " + USAGE)


def _clean_output(text: str, folder: Path) -> str:
    return text.replace(str(folder), "/workspace/sample").replace("\\\\", "\\")[:MAX_OUTPUT_BYTES]


def _run(argv: list[str], folder: Path, *, cwd: Path) -> dict[str, Any]:
    # Deliberately pass a MINIMAL environment. No connected AI keys, GitHub
    # credentials, Vercel env, proxy config, or API tokens reach the process.
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "PYTHONPATH": str(RUNTIME_ROOT),
        "HOME": str(folder),
        "TMPDIR": str(folder),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }
    started = time.perf_counter()
    try:
        result = subprocess.run(
            argv, cwd=cwd, env=env, shell=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=SUBPROCESS_TIMEOUT_SECONDS,
            check=False, text=True, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124, "stdout": "", "stderr": "Demo timeout (5s).",
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "status": "timeout",
        }
    return {
        "exit_code": result.returncode,
        "stdout": _clean_output(result.stdout, folder),
        "stderr": _clean_output(result.stderr, folder),
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "status": "completed",
    }


def execute(command: str) -> dict[str, Any]:
    """Execute one validated CLI call with a NEW isolated demo project.

    Snapshot operations are chained in-process for one demonstration only;
    nothing from this function persists to a second HTTP request.
    """
    argv, kind = _parse(command)
    with tempfile.TemporaryDirectory(prefix="omniforge-public-demo-") as directory:
        root = Path(directory)
        project = root / "sample"
        project.mkdir()
        (project / "app.py").write_text(
            "from hashlib import sha256\n"
            "def greet(name: str) -> str:\n"
            "    return f'Hello, {name}'\n"
            "print(greet('OmniForge'))\n",
            encoding="utf-8",
        )
        (project / "pyproject.toml").write_text(
            '[project]\nname = "sample-demo"\nversion = "0.0.1"\n', encoding="utf-8"
        )
        (project / "errors.log").write_text(
            "2026-10-25 ERROR TimeoutError: demo upstream timed out\n",
            encoding="utf-8"
        )
        steps = []
        if kind == "provenance":
            action = argv[0]
            if action != "init":
                first = _run(
                    [sys.executable, "-m", "omniforge.provenance_v2_cli",
                     "init", "--project", str(project)], root, cwd=project,
                )
                steps.append({"command": "ofprov init", **first})
                if first["exit_code"]:
                    return {"ok": False, "mode": "server-python-actual-cli",
                            "command": command, "steps": steps, "stdout": "",
                            "stderr": "Unable to initialize disposable ledger.",
                            "exit_code": first["exit_code"], "disclaimer": SAFE_DEMO}
            if action in ("verify", "audit", "proof", "tamper-demo"):
                second = _run(
                    [sys.executable, "-m", "omniforge.provenance_v2_cli",
                     "snapshot", "--project", str(project)], root, cwd=project,
                )
                steps.append({"command": "ofprov snapshot", **second})
                if second["exit_code"]:
                    return {"ok": False, "mode": "server-python-actual-cli",
                            "command": command, "steps": steps, "stdout": "",
                            "stderr": "Unable to snapshot disposable project.",
                            "exit_code": second["exit_code"], "disclaimer": SAFE_DEMO}
            if action == "tamper-demo":
                (project / "app.py").write_text("print('the source changed')\n", encoding="utf-8")
                steps.append({"command": "# Modify app.py after snapshot",
                              "stdout": "Modified sample app.py to simulate tampering.",
                              "stderr": "", "exit_code": 0, "status": "fixture-change", "duration_ms": 0})
                action = "verify"
            argv = [sys.executable, "-m", "omniforge.provenance_v2_cli",
                    action, "--project", str(project)]
            if action == "verify":
                argv.append("--check-files")
        elif kind == "inspect":
            argv.append(str(project))
        final = _run(argv, root, cwd=project)
        return {
            "ok": final["exit_code"] == 0,
            "mode": "server-python-actual-cli",
            "command": command,
            "python": sys.version.split()[0],
            "steps": steps,
            **final,
            "disclaimer": SAFE_DEMO +
                " The server does not accept arbitrary code, network actions or filesystem paths.",
        }


def execute_batch(commands: list[str]) -> dict[str, Any]:
    """Run up to four prevalidated commands in ONE ephemeral sample project.

    An entire batch is checked against _parse before any command executes.
    Every CLI operation is a real Python subprocess, never a shell command.
    """
    if (not isinstance(commands, list) or not 1 <= len(commands) <= MAX_BATCH_COMMANDS
            or any(not isinstance(c, str) for c in commands)):
        raise DemoError("Supply 1 to 4 separate command lines.")
    validated = [_parse(command) for command in commands]
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="omniforge-batch-demo-") as directory:
        root = Path(directory)
        project = root / "sample"
        project.mkdir()
        (project / "app.py").write_text(
            "from hashlib import sha256\n"
            "def greet(name: str) -> str:\n"
            "    return f'Hello, {name}'\n"
            "print(greet('OmniForge'))\n", encoding="utf-8",
        )
        (project / "pyproject.toml").write_text(
            '[project]\nname = "sample-demo"\nversion = "0.0.1"\n', encoding="utf-8",
        )
        (project / "errors.log").write_text(
            "2026-10-25 ERROR TimeoutError: demo upstream timed out\n", encoding="utf-8",
        )
        completed: list[dict[str, Any]] = []
        for command, (argv, kind) in zip(commands, validated, strict=True):
            intermediate: list[dict[str, Any]] = []
            action = argv[0] if kind == "provenance" else ""
            if kind == "provenance":
                ledger_dir = project / ".of-provenance"
                if action != "init" and not ledger_dir.exists():
                    initial = _run(
                        [sys.executable, "-m", "omniforge.provenance_v2_cli",
                         "init", "--project", str(project)], root, cwd=project,
                    )
                    intermediate.append({"command": "ofprov init", **initial})
                    if initial["exit_code"]:
                        completed.append({
                            "command": command, "ok": False, "expected_tamper": False,
                            "stdout": "", "stderr": initial["stderr"],
                            "exit_code": initial["exit_code"],
                            "duration_ms": initial["duration_ms"],
                            "subprocesses": intermediate,
                        })
                        continue
                chain = project / ".of-provenance" / "chain.jsonl"
                if (action in ("verify", "audit", "proof", "tamper-demo")
                        and chain.is_file() and chain.stat().st_size == 0):
                    sampled = _run(
                        [sys.executable, "-m", "omniforge.provenance_v2_cli",
                         "snapshot", "--project", str(project)], root, cwd=project,
                    )
                    intermediate.append({"command": "ofprov snapshot", **sampled})
                    if sampled["exit_code"]:
                        completed.append({
                            "command": command, "ok": False, "expected_tamper": False,
                            "stdout": "", "stderr": sampled["stderr"],
                            "exit_code": sampled["exit_code"],
                            "duration_ms": sampled["duration_ms"],
                            "subprocesses": intermediate,
                        })
                        continue
                if action == "tamper-demo":
                    (project / "app.py").write_text(
                        "print('changed AFTER snapshot')\n", encoding="utf-8",
                    )
                    intermediate.append({
                        "command": "# change sample app.py after snapshot",
                        "stdout": "Changed sample bytes; no real user files accessed.",
                        "stderr": "", "exit_code": 0,
                        "status": "fixture-change", "duration_ms": 0,
                    })
                    action = "verify"
                argv = [sys.executable, "-m", "omniforge.provenance_v2_cli",
                        action, "--project", str(project)]
                if action == "verify":
                    argv.append("--check-files")
            elif kind == "inspect":
                argv = [*argv, str(project)]
            final = _run(argv, root, cwd=project)
            tamper_expected = False
            if kind == "provenance" and command == "ofprov tamper-demo":
                try:
                    result_json = json.loads(final["stdout"])
                    tamper_expected = (
                        final["exit_code"] == 1 and isinstance(result_json, dict)
                        and result_json.get("ok") is False
                    )
                except (ValueError, TypeError):
                    pass
            completed.append({
                "command": command, "ok": final["exit_code"] == 0 or tamper_expected,
                "expected_tamper": tamper_expected,
                "stdout": final["stdout"], "stderr": final["stderr"],
                "exit_code": final["exit_code"], "duration_ms": final["duration_ms"],
                "subprocesses": intermediate,
            })
        return {
            "ok": all(result["ok"] for result in completed),
            "mode": "server-python-actual-cli-batch",
            "commands": len(completed), "results": completed,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "disclaimer": "All lines share one disposable sample project for "
                "this request only. State is destroyed afterwards. "
                "Every line must pass a strict allowlist; no shell commands.",
        }


class handler(BaseHTTPRequestHandler):
    """Vercel Python Functions entrypoint, reachable at /api/terminal."""

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        # Health must run a real CLI subprocess, not merely report Python ready.
        check = _run(
            [sys.executable, "-m", "omniforge.cli", "--version"],
            RUNTIME_ROOT, cwd=RUNTIME_ROOT,
        )
        ready = check["exit_code"] == 0 and BUNDLED_VERSION in (
            check["stdout"] + check["stderr"]
        )
        self._json(200 if ready else 503, {
            "ok": ready, "engine": "OmniForge v1.3.1 / real Python subprocess",
            "package_version": BUNDLED_VERSION,
            "package_source": "bundled-canonical-source",
            "self_test": "PASS" if ready else "FAIL: CLI subprocess package import",
            "runtime": sys.version.split()[0],
            "scope": "strict allowlist + isolated temporary project per request; up to 4 commands share a single temporary batch project",
            "batch_max_commands": MAX_BATCH_COMMANDS,
            "samples": [
                "python --version", "omniforge doctor",
                'omniforge search "API errors"',
                'omniforge related "python crash"',
                'omniforge plan "debug python errors"',
                "omniforge budget --selected log-triage",
                "omniforge load python-symbols",
                "ofprov snapshot", "ofprov verify", "ofprov tamper-demo",
            ],
        })

    def do_POST(self) -> None:
        origin = self.headers.get("Origin", "")
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "")
        if origin and not (
            origin.startswith("https://")
            or origin.startswith("http://localhost:")
            or origin.startswith("http://127.0.0.1:")
        ):
            self._json(403, {"ok": False, "error": "Invalid origin."})
            return
        if origin and origin.rstrip("/").split("://", 1)[-1] != host:
            self._json(403, {"ok": False, "error": "Same-origin requests only."})
            return
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self._json(400, {"ok": False, "error": "Malformed request length."})
            return
        if size < 1 or size > MAX_REQUEST_BYTES:
            self._json(413, {"ok": False, "error": "Request too large (max 1024 bytes)."})
            return
        if "application/json" not in self.headers.get("Content-Type", ""):
            self._json(415, {"ok": False, "error": "Expected application/json."})
            return
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(payload, dict):
                raise DemoError("Expected JSON object.")
            if set(payload) == {"command"}:
                response = execute(payload["command"])
            elif set(payload) == {"commands"}:
                response = execute_batch(payload["commands"])
            else:
                raise DemoError('Request format: {"command":"omniforge doctor"} or '
                                '{"commands":["omniforge doctor","ofprov verify"]}')
        except (DemoError, ValueError, UnicodeError) as exc:
            self._json(400, {"ok": False, "error": str(exc), "usage": USAGE})
            return
        except Exception:
            # Never expose traces / environment variables to anonymous callers.
            self._json(500, {"ok": False, "error": "Demo service unavailable; check deployment logs."})
            return
        self._json(200, response)
