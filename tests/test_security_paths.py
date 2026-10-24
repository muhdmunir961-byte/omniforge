"""Regression tests for symlinked project-write destinations."""
from pathlib import Path
import pytest
from omniforge.core import install_skill, secure_project_path
from omniforge.vscode import configure_vscode


def linked(parent: Path, target: Path) -> None:
    try:
        parent.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")


@pytest.mark.parametrize("location", [".agents", ".agents/skills"])
@pytest.mark.parametrize("force", [False, True])
def test_install_refuses_symlinked_parent(tmp_path, location, force):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (outside / "sentinel.txt").write_text("untouched")
    dest = project / location
    dest.parent.mkdir(parents=True, exist_ok=True)
    linked(dest, outside)
    with pytest.raises(ValueError, match="symlink"):
        install_skill("log-triage", "codex", project, force=force)
    assert (outside / "sentinel.txt").read_text() == "untouched"
    assert not (outside / "log-triage").exists()


@pytest.mark.parametrize("force", [False, True])
def test_install_refuses_symlinked_skill_directory(tmp_path, force):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = project / ".agents" / "skills" / "log-triage"
    target.parent.mkdir(parents=True)
    linked(target, outside)
    (outside / "sentinel.txt").write_text("untouched")
    with pytest.raises(ValueError, match="symlink"):
        install_skill("log-triage", "codex", project, force=force)
    assert (outside / "sentinel.txt").read_text() == "untouched"


@pytest.mark.parametrize("location", [".vscode", ".github", ".github/instructions"])
def test_vscode_rejects_symlinked_parent(tmp_path, location):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    dest = project / location
    dest.parent.mkdir(parents=True, exist_ok=True)
    linked(dest, outside)
    with pytest.raises(ValueError, match="symlink"):
        configure_vscode(project)
    assert not list(outside.iterdir())


@pytest.mark.parametrize("location", [
    ".vscode/mcp.json",
    ".github/instructions/omniforge.instructions.md",
])
def test_vscode_refuses_symlinked_file(tmp_path, location):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep")
    dest = project / location
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")
    with pytest.raises(ValueError, match="symlink"):
        configure_vscode(project, force=True)
    assert outside.read_text() == "keep"


def test_path_helper_rejects_traversal(tmp_path):
    with pytest.raises(ValueError, match="Unsafe"):
        secure_project_path(tmp_path, "../outside")
    assert secure_project_path(tmp_path, "skills", "log-triage") == tmp_path / "skills" / "log-triage"


def test_normal_install_and_vscode_still_work(tmp_path):
    dest = install_skill("log-triage", "codex", tmp_path)
    assert (dest / "SKILL.md").is_file()
    files = configure_vscode(tmp_path)
    assert all(path.is_file() for path in files)
