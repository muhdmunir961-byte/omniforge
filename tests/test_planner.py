from omniforge.planner import related, plan
from omniforge.cli import main

def test_synonym_search_api():
    results = related("REST endpoint", limit=5)
    assert any(x["name"] == "api-probe" for x in results)

def test_synonym_search_firmware():
    results = related("ESP32 serial device")
    assert any(x["name"] == "firmware-preflight" for x in results)

def test_plan_requires_approval():
    result = plan("debug python errors")
    assert result["mode"] == "dry-run"
    assert result["requires_human_approval"]
    assert all(step["skill"] for step in result["steps"])

def test_no_unmatched_plan():
    assert plan("zzzznonmatchingzzzz")["steps"] == []

def test_invalid_limit():
    import pytest
    with pytest.raises(ValueError):
        related("api", limit=0)

def test_cli_commands(capsys):
    assert main(["related", "sqlite database"]) == 0
    assert "sqlite-inspector" in capsys.readouterr().out
    assert main(["plan", "analyze server logs"]) == 0
    assert '"dry-run"' in capsys.readouterr().out
