"""OmniForge local command-line application."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from . import __version__
from .core import (AGENT_LOCATIONS, audit_skill, bundled_names, bundled_root, catalog,
                   forge_skill, install_skill, validate_skill)
from .router import index, load_skill, search_skills, token_report
from .vscode import configure_vscode


def as_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def repo_recon(repo: Path) -> dict:
    """Local reconnaissance without executing any files or following symlinks."""
    root = repo.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    markers = {
        "python": ["pyproject.toml", "requirements.txt", "setup.py"],
        "javascript": ["package.json", "pnpm-lock.yaml", "yarn.lock"],
        "rust": ["Cargo.toml"], "go": ["go.mod"],
        "arduino": ["platformio.ini", "arduino-cli.yaml"],
        "docker": ["Dockerfile", "compose.yaml", "docker-compose.yml"],
    }
    detected = [name for name, patterns in markers.items() if any((root / f).is_file() and not (root / f).is_symlink() for f in patterns)]
    top = sorted(p.name for p in root.iterdir() if not p.is_symlink())[:75]
    return {"project": str(root), "detected": detected, "top_level": top,
            "suggestions": search_skills(" ".join(detected), limit=3) if detected else []}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="omniforge", description="OmniForge v1.0 — agent skills without loading everything")
    ap.add_argument("--version", action="version", version=f"OmniForge {__version__}")
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("doctor", help="inspect local capabilities")
    sub.add_parser("list", help="list compact bundled skill summaries")
    s = sub.add_parser("search", help="search bundled skills without reading their full bodies")
    s.add_argument("query"); s.add_argument("--limit", type=int, default=5)
    l = sub.add_parser("load", help="expand exactly one bundled SKILL.md")
    l.add_argument("name", choices=bundled_names())
    l.add_argument("--max-chars", type=int, default=12000)
    b = sub.add_parser("budget", help="rough estimate of lazy skill context consumption")
    b.add_argument("--selected", choices=bundled_names())
    c = sub.add_parser("catalog", help="search upstream GitHub tool candidates (not integrations)")
    c.add_argument("query", nargs="?", default="")
    c.add_argument("--category"); c.add_argument("--limit", type=int, default=25)
    i = sub.add_parser("install", help="install an audited local skill into a coding agent")
    i.add_argument("name"); i.add_argument("--agent", choices=sorted(AGENT_LOCATIONS), default="universal")
    i.add_argument("--project", type=Path, default=Path.cwd())
    i.add_argument("--source", type=Path, help="optional local skill directory")
    i.add_argument("--force", action="store_true", help="replace same skill folder (destructive)")
    a = sub.add_parser("audit", help="non-executing structural and heuristic security audit")
    a.add_argument("path", type=Path)
    v = sub.add_parser("validate", help="check portable SKILL.md metadata")
    v.add_argument("path", type=Path)
    f = sub.add_parser("forge", help="generate non-executable skill scaffold for trusted CLI")
    f.add_argument("name"); f.add_argument("--description", required=True)
    f.add_argument("--command", required=True); f.add_argument("--output", type=Path, default=Path.cwd())
    vs = sub.add_parser("setup-vscode", help="add VS Code MCP and short optional skill instructions")
    vs.add_argument("--project", type=Path, default=Path.cwd()); vs.add_argument("--force", action="store_true")
    rr = sub.add_parser("inspect", help="read-only local project reconnaissance")
    rr.add_argument("project", nargs="?", type=Path, default=Path.cwd())
    sem = sub.add_parser("related", help="synonym-aware offline skill search")
    sem.add_argument("query"); sem.add_argument("--limit", type=int, default=5)
    pl = sub.add_parser("plan", help="generate reviewable skill workflow without executing it")
    pl.add_argument("task"); pl.add_argument("--limit", type=int, default=3)
    sub.add_parser("mcp", help="start stdio MCP tool server")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "doctor":
            as_json({"name": "OmniForge", "version": __version__, "python": sys.version.split()[0],
                     "skills": bundled_names(), "candidates": len(catalog()),
                     "agents": sorted(AGENT_LOCATIONS), "executable": shutil.which("omniforge"),
                     "mode": "local-only; no LLM subscription or API key required"})
        elif args.action == "list":
            as_json(index())
        elif args.action == "search":
            if not 1 <= args.limit <= 20:
                raise ValueError("--limit must be 1..20")
            as_json(search_skills(args.query, limit=args.limit))
        elif args.action == "load":
            as_json(load_skill(args.name, max_chars=args.max_chars))
        elif args.action == "budget":
            as_json(token_report(chosen=args.selected))
        elif args.action == "catalog":
            query = args.query.lower()
            found = [t for t in catalog() if
                     (not args.category or args.category.lower() == t["category"].lower())
                     and query in " ".join(str(x) for x in t.values()).lower()]
            as_json({"count": len(found), "results": found[:max(0, min(args.limit, 200))],
                     "notice": "Discovery candidates only; external repos not installed or verified."})
        elif args.action == "install":
            as_json({"installed": str(install_skill(args.name, args.agent, args.project,
                                                   source=args.source, force=args.force))})
        elif args.action == "audit":
            report = audit_skill(args.path)
            as_json(report)
            return int(bool(report["structural_errors"] or report["findings"]))
        elif args.action == "validate":
            issues = validate_skill(args.path)
            as_json({"ok": not issues, "problems": issues})
            return int(bool(issues))
        elif args.action == "forge":
            as_json({"created": str(forge_skill(args.output, args.name, args.description, args.command))})
        elif args.action == "setup-vscode":
            as_json({"written": [str(p) for p in configure_vscode(args.project, force=args.force)]})
        elif args.action == "inspect":
            as_json(repo_recon(args.project))
        elif args.action == "related":
            from .planner import related
            as_json(related(args.query, limit=args.limit))
        elif args.action == "plan":
            from .planner import plan
            as_json(plan(args.task, limit=args.limit))
        elif args.action == "mcp":
            from .mcp import serve
            serve()
        else:
            raise ValueError("Unknown action")
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"omniforge: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
