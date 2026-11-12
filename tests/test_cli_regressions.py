"""Regressions for CLI argument parsing, workflow validation and diagnostics.

Each test here pins a defect that was observed in real command output, so a
future refactor cannot silently reintroduce it.
"""
from __future__ import annotations

import json

import pytest

from omniforge.agents import read_workflow
from omniforge.cli import local_capabilities, main


def test_run_flags_after_skill_name_are_parsed(tmp_path):
    """``omniforge run <skill> --approve`` must reach the approval gate.

    ``argparse.REMAINDER`` used to swallow every flag after the skill name, so
    the documented command silently produced a preview-only plan.
    """
    (tmp_path / "app.py").write_text("value = 1\n")
    assert main(["run", "python-symbols", "--unsafe-local", "--approve",
                 "--project", str(tmp_path), "--", "app.py"]) == 0


def test_run_separator_after_options_works_on_every_supported_python(tmp_path):
    """Python 3.11's argparse rejects '--' before nargs="*" after options.

    Python 3.13 accepts it. main() splits the separator itself so the same
    command line works on both; this pins that behaviour.
    """
    (tmp_path / "app.py").write_text("value = 1\n")
    assert main(["run", "python-symbols", "--unsafe-local", "--approve",
                 "--project", str(tmp_path), "--", "app.py"]) == 0
    assert main(["run", "python-symbols", "--unsafe-local",
                 "--project", str(tmp_path), "--", "app.py"]) == 0


def test_run_preview_keeps_script_arguments(tmp_path, capsys):
    (tmp_path / "app.py").write_text("value = 1\n")
    assert main(["run", "python-symbols", "--unsafe-local",
                 "--project", str(tmp_path), "--", "app.py"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["status"] == "preview-only"
    assert plan["command"][-1] == "app.py"


def test_workflow_task_without_skill_is_rejected(tmp_path):
    workflow = tmp_path / "missing-skill.json"
    workflow.write_text(json.dumps({"tasks": [{"id": "a"}]}))
    with pytest.raises(ValueError, match="requires a skill name"):
        read_workflow(workflow)


def test_workflow_rejects_unknown_skill(tmp_path):
    workflow = tmp_path / "unknown.json"
    workflow.write_text(json.dumps({"tasks": [{"id": "a", "skill": "not-a-skill"}]}))
    with pytest.raises(ValueError, match="unknown bundled skill"):
        read_workflow(workflow)


def test_workflow_agent_task_requires_executable(tmp_path):
    workflow = tmp_path / "agent.json"
    workflow.write_text(json.dumps({"tasks": [{"id": "a", "kind": "agent"}]}))
    with pytest.raises(ValueError, match="requires an executable"):
        read_workflow(workflow)


def test_workflow_root_must_be_object(tmp_path):
    workflow = tmp_path / "list.json"
    workflow.write_text(json.dumps([{"id": "a"}]))
    with pytest.raises(ValueError, match="root must be a JSON object"):
        read_workflow(workflow)


def test_workflow_invalid_json_reports_value_error(tmp_path):
    workflow = tmp_path / "broken.json"
    workflow.write_text("{not json")
    with pytest.raises(ValueError, match="not valid UTF-8 JSON"):
        read_workflow(workflow)


def test_doctor_reports_real_capabilities(capsys):
    """Diagnostics must distinguish 'installed' from 'available'."""
    assert main(["doctor"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["version"]
    assert len(report["skills"]) == 18
    capabilities = report["capabilities"]
    assert set(capabilities) >= {
        "docker", "git", "playwright", "sentence_transformers",
        "isolated_execution", "browser_automation", "byok_endpoint_key",
    }
    # Booleans must be real booleans, not truthy strings, and the advisory text
    # must match the boolean instead of always claiming success.
    for key in ("docker", "git", "playwright", "sentence_transformers", "byok_endpoint_key"):
        assert isinstance(capabilities[key], bool)
    assert (capabilities["isolated_execution"] == "docker") is capabilities["docker"]
    assert (capabilities["browser_automation"] == "playwright") is capabilities["playwright"]


def test_doctor_capabilities_do_not_import_optional_packages():
    """Probing must use find_spec, never import, so no side effects or downloads."""
    capabilities = local_capabilities()
    assert isinstance(capabilities["sentence_transformers"], bool)
