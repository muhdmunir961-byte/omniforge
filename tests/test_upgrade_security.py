"""Upgrade-only security regressions; skipped until optional v1.1 modules ship."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest


def test_mcp_does_not_accept_model_approval(tmp_path):
    pytest.importorskip("omniforge.runtime")
    from omniforge.mcp import dispatch
    from omniforge.runtime import execute_run
    from omniforge.browser import browser_session
    cases = [
        ("OMNIFORGE_MCP_EXECUTION", "omniforge_run",
         {"name": "firmware-preflight", "project": str(tmp_path), "approve": True}),
        ("OMNIFORGE_MCP_BROWSER", "omniforge_browser",
         {"url": "https://example.org", "project": str(tmp_path), "approve": True}),
    ]
    for env_name, name, args in cases:
        with patch.dict("os.environ", {env_name: "1"}):
            reply = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": name, "arguments": args}})
        payload = json.loads(reply["result"]["content"][0]["text"])
        assert payload["status"] == "preview-only"
    # Model-supplied approval must not even be advertised as a tool field.
    tools = dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    for tool in tools:
        if tool["name"] in {"omniforge_run", "omniforge_browser"}:
            assert "approve" not in tool["inputSchema"]["properties"]


def test_autocode_rejects_linked_backup_root(tmp_path):
    pytest.importorskip("omniforge.autocode")
    from omniforge.autocode import apply_proposal, _hash
    target = tmp_path / "main.py"
    target.write_text("original")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    try:
        (tmp_path / ".omniforge").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(str(exc))
    proposal = {"edits": [{"path": "main.py", "sha256": _hash(target.read_bytes()),
                           "new_content": "updated"}]}
    with pytest.raises(ValueError, match="symlink"):
        apply_proposal(proposal, tmp_path, approve=True)
    assert target.read_text() == "original"
    assert not list(outside.iterdir())


def test_browser_rejects_linked_screenshot(tmp_path):
    pytest.importorskip("omniforge.browser")
    from omniforge.browser import browser_session
    outside = tmp_path / "outside.png"
    outside.write_text("keep")
    try:
        (tmp_path / "shot.png").symlink_to(outside)
    except OSError as exc:
        pytest.skip(str(exc))
    with pytest.raises(ValueError, match="symlink"):
        browser_session("https://example.org", project=tmp_path, screenshot="shot.png")
    assert outside.read_text() == "keep"
