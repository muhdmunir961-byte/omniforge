"""Regression tests for low-context, conditional source and skill reads."""
import hashlib
import json
from pathlib import Path

import pytest

from omniforge.context import read_context
from omniforge.router import load_skill, token_report
from omniforge.cli import main
from omniforge.mcp import dispatch


def test_conditional_read_suppresses_unchanged_content(tmp_path):
    f = tmp_path / "demo.py"
    f.write_text("x = 1\ny = 2\n", encoding="utf-8")
    first = read_context(tmp_path, "demo.py")
    assert first["status"] == "changed" and "1: x = 1" in first["content"]
    assert first["next_line"] is None
    again = read_context(tmp_path, "demo.py", known_sha256=first["sha256"])
    assert again["status"] == "unchanged"
    assert again["content"] == "" and again["estimated_tokens"] == 0
    f.write_text("x = 1\ny = 3\n", encoding="utf-8")
    changed = read_context(tmp_path, "demo.py", known_sha256=first["sha256"])
    assert changed["status"] == "changed" and changed["sha256"] != first["sha256"]


def test_targeted_range_and_hard_limits(tmp_path):
    (tmp_path / "a.ts").write_text("\n".join(f"line{i}" for i in range(1, 151)) + "\n")
    result = read_context(tmp_path, "a.ts", start_line=50, max_lines=3, max_chars=256)
    assert result["start_line"] == 50 and result["end_line"] == 52
    assert result["next_line"] == 53 and "49:" not in result["content"]
    with pytest.raises(ValueError):
        read_context(tmp_path, "a.ts", max_lines=1000)
    with pytest.raises(ValueError):
        read_context(tmp_path, "a.ts", max_chars=50000)
    with pytest.raises(ValueError):
        read_context(tmp_path, "a.ts", known_sha256="invalid")


@pytest.mark.parametrize("path", [
    "../outside.py", "/etc/passwd", ".env", ".github/workflows/ci.yml",
    "node_modules/main.js", "src/../../a.py", "credentials/key.json",
    "README.txt", "a\\b.py"
])
def test_rejects_unsafe_or_unwanted_paths(tmp_path, path):
    with pytest.raises(ValueError):
        read_context(tmp_path, path)


def test_symlink_path_rejected(tmp_path):
    outside = tmp_path.parent / "other.py"
    outside.write_text("secret = 1")
    (tmp_path / "linked.py").symlink_to(outside)
    with pytest.raises(ValueError):
        read_context(tmp_path, "linked.py")


def test_cli_and_skill_conditional_load(tmp_path, capsys):
    (tmp_path / "demo.py").write_text("answer = 42\n")
    assert main(["context", "demo.py", "--project", str(tmp_path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "changed"
    assert main(["context", "demo.py", "--project", str(tmp_path),
                 "--known-sha256", first["sha256"]]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "unchanged"
    skill = load_skill("log-triage")
    assert skill["sha256"] == hashlib.sha256(skill["content"].encode()).hexdigest()
    unchanged = load_skill("log-triage", known_sha256=skill["sha256"])
    assert unchanged["content"] == "" and unchanged["estimated_tokens"] == 0
    assert token_report(chosen="log-triage")["metadata_estimated_tokens"] > 0


def test_mcp_conditional_skill_load():
    initial = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "omniforge_load",
                                   "arguments": {"name": "log-triage"}}})
    digest = json.loads(initial["result"]["content"][0]["text"])["sha256"]
    repeated = dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                         "params": {"name": "omniforge_load",
                                    "arguments": {"name": "log-triage",
                                                  "known_sha256": digest}}})
    result = json.loads(repeated["result"]["content"][0]["text"])
    assert result["status"] == "unchanged" and result["content"] == ""
