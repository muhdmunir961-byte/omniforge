"""Portable skill package management and non-executing security inspection."""
from __future__ import annotations

import json
import os
import re
import shutil
from importlib.resources import files
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DANGER_PATTERNS = {
    "pipe-to-shell": re.compile(r"\b(?:curl|wget)\b[^\n]{0,200}\|\s*(?:ba)?sh\b", re.I),
    "destructive-delete": re.compile(r"\brm\s+-[a-z]*[rf][a-z]*\s+[/~]", re.I),
    "credential-reference": re.compile(r"(?:\.ssh/|\.aws/credentials|\b(?:API_KEY|ACCESS_TOKEN|PRIVATE_KEY)\b)", re.I),
    "privileged-command": re.compile(r"\b(?:sudo|chmod\s+777)\b", re.I),
    "encoded-evaluation": re.compile(r"\b(?:base64\s+-d|eval\s*\(|exec\s*\()", re.I),
}
AGENT_LOCATIONS = {
    "codex": ".agents/skills", "claude": ".claude/skills", "cursor": ".cursor/skills",
    "opencode": ".opencode/skills", "copilot": ".github/skills",
    "gemini": ".gemini/skills", "universal": ".agents/skills",
}


def data_root() -> Path:
    return Path(str(files("omniforge").joinpath("data")))


def catalog() -> list[dict]:
    return json.loads((data_root() / "catalog.json").read_text(encoding="utf-8"))


def bundled_root() -> Path:
    return data_root() / "skills"


def bundled_names() -> list[str]:
    return sorted(path.name for path in bundled_root().iterdir() if (path / "SKILL.md").is_file())


def skill_metadata(path: Path) -> dict[str, str]:
    """Read *only frontmatter*. Skill body is never loaded on catalog listing."""
    file = path / "SKILL.md"
    if not file.is_file() or file.is_symlink():
        raise ValueError("SKILL.md missing or symlinked")
    if file.stat().st_size > 300_000:
        raise ValueError("SKILL.md too large")
    with file.open(encoding="utf-8") as stream:
        if stream.readline().strip() != "---":
            raise ValueError("YAML frontmatter missing")
        lines = []
        for line in stream:
            if line.strip() == "---":
                break
            if len(lines) > 80:
                raise ValueError("Too many frontmatter lines")
            lines.append(line)
        else:
            raise ValueError("Unterminated frontmatter")
    # Extract only common scalar fields; no YAML deserialization or code evaluation.
    meta = {}
    for line in lines:
        m = re.match(r"^([a-z][a-z-]*):\s*(.*?)\s*$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip('"\'')
    return meta


def validate_skill(path: Path) -> list[str]:
    try:
        meta = skill_metadata(path)
    except (OSError, ValueError, UnicodeError) as exc:
        return [str(exc)]
    issues = []
    name = meta.get("name", "")
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        issues.append("name must be lower-case hyphenated and <=64 chars")
    elif name != path.name:
        issues.append("name must match folder")
    description = meta.get("description", "")
    if not description or len(description) > 1024:
        issues.append("description required, max 1024 chars")
    return issues


def skill_info(path: Path) -> dict:
    problems = validate_skill(path)
    if problems:
        raise ValueError("; ".join(problems))
    meta = skill_metadata(path)
    return {"name": meta["name"], "description": meta["description"], "path": str(path)}


def audit_skill(path: Path) -> dict:
    """Heuristic inspection only. No execution; not a security guarantee."""
    if not path.is_dir() or path.is_symlink():
        raise ValueError("Expected a real directory")
    findings = []
    checked_files = 0
    for item in sorted(path.rglob("*")):
        rel = str(item.relative_to(path))
        if item.is_symlink():
            findings.append({"path": rel, "line": 0, "rule": "symlink"})
            continue
        if not item.is_file() or item.suffix.lower() not in {".md", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml"}:
            continue
        if item.stat().st_size > 1_000_000:
            findings.append({"path": rel, "line": 0, "rule": "large-unscanned-file"})
            continue
        checked_files += 1
        for line_no, line in enumerate(item.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for rule, regex in DANGER_PATTERNS.items():
                if regex.search(line):
                    findings.append({"path": rel, "line": line_no, "rule": rule})
    return {
        "skill": path.name, "checked_files": checked_files,
        "structural_errors": validate_skill(path), "findings": findings,
        "disclaimer": "Heuristic audit only; review dependencies and commands before execution.",
    }


def resolve_source(name: str, source: Path | None = None) -> Path:
    if source is None:
        if name not in bundled_names():
            raise ValueError(f"Unknown bundled skill: {name}")
        path = bundled_root() / name
    else:
        path = source.expanduser().resolve()
        if path.name != name:
            raise ValueError("Skill name must match source folder")
    problems = validate_skill(path)
    if problems:
        raise ValueError("; ".join(problems))
    if any(p.is_symlink() for p in path.rglob("*")):
        raise ValueError("Skill contains symlinks; refusing to install")
    return path



def secure_project_path(project: Path, *parts: str) -> Path:
    """Reject symlinks beneath the project before filesystem writes.

    This limits accidental traversal; it cannot prevent a concurrent
    malicious process from changing paths after validation (TOCTOU).
    """
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project must be an existing directory")
    current = root
    for part in parts:
        segment = Path(part)
        if segment.is_absolute() or any(value == ".." for value in segment.parts):
            raise ValueError("Unsafe project destination")
        for component in segment.parts:
            if component in ("", "."):
                continue
            current = current / component
            # On Windows, junctions are reparse points even when is_symlink()
            # is False. Never traverse them in a project write destination.
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise ValueError(f"Refusing symlinked destination: {current}")
            # On Windows, resolve(strict=False) is not stable for paths being
            # created concurrently, and can falsely report a path escape.
            # Every component has been appended from the resolved root and
            # reparse points are rejected above; retain the stricter POSIX check.
            if os.name != "nt" and not current.resolve(strict=False).is_relative_to(root):
                raise ValueError("Destination escapes project")
    return current


def install_skill(name: str, agent: str, project: Path, *, source: Path | None = None, force: bool = False) -> Path:
    if agent not in AGENT_LOCATIONS:
        raise ValueError(f"Unknown agent: {agent}")
    src = resolve_source(name, source)
    destination = secure_project_path(project, AGENT_LOCATIONS[agent], name)
    if destination.exists() or destination.is_symlink():
        if not force:
            raise FileExistsError(f"{destination} already exists; use --force")
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("Refusing to replace symlink or non-directory")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, destination, symlinks=False)
    return destination


def forge_skill(output: Path, name: str, description: str, command: str) -> Path:
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        raise ValueError("Invalid skill name")
    if not description or len(description) > 900 or '\n' in description or '\r' in description:
        raise ValueError("Invalid description")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", command):
        raise ValueError("Provide an executable name only, not shell code")
    target = output.expanduser().resolve() / name
    target.mkdir(parents=True, exist_ok=False)
    sanitized = description.replace('"', "'")
    (target / "SKILL.md").write_text(
        f'---\nname: {name}\ndescription: "{sanitized}"\n---\n\n'
        f'# {name}\n\nUse `{command}` when the current task needs it.\n\n'
        '1. Confirm the CLI exists and inspect its documented flags.\n'
        '2. Start read-only; do not execute untrusted commands.\n'
        '3. Get human approval for writes, network access, or secrets.\n'
        '4. Verify the result with tests and summarize evidence.\n\n'
        '**Status:** Documentation scaffold only; not a tested integration.\n', encoding="utf-8")
    return target
