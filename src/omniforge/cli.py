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
from .semantic import hybrid_search, embedding_search
from .planner import related, plan
from .runtime import prepare_run, execute_run
from .agents import execute_workflow
from .browser import browser_session, load_actions
from .autocode import request_edits, apply_proposal
from .provenance import build_manifest, check_manifest


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
    s.add_argument("--mode", choices=("keyword", "hybrid", "embeddings"), default="hybrid")
    s.add_argument("--model-path", help="already-installed local sentence embedding model")
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
    run = sub.add_parser("run", help="permission-gated bundled skill execution (Docker by default)")
    run.add_argument("name", choices=bundled_names())
    run.add_argument("--project", type=Path, default=Path.cwd())
    run.add_argument("--unsafe-local", action="store_true", help="host execution is NOT sandboxed")
    run.add_argument("--allow-network", action="store_true")
    run.add_argument("--approve", action="store_true")
    run.add_argument("--timeout", type=int, default=30)
    run.add_argument("args", nargs=argparse.REMAINDER, help="script args, after --")
    ag = sub.add_parser("orchestrate", help="run a validated dependency-ordered skill/agent workflow")
    ag.add_argument("workflow", type=Path)
    ag.add_argument("--project", type=Path, default=Path.cwd())
    ag.add_argument("--approve", action="store_true")
    ag.add_argument("--unsafe-local", action="store_true")
    ag.add_argument("--allow-network", action="store_true")
    ag.add_argument("--allow-command", action="append", default=[])
    ag.add_argument("--workers", type=int, default=2)
    br = sub.add_parser("browser", help="opt-in Playwright page visit and deterministic browser actions")
    br.add_argument("--url", required=True)
    br.add_argument("--actions", type=Path)
    br.add_argument("--screenshot")
    br.add_argument("--project", type=Path, default=Path.cwd())
    br.add_argument("--approve", action="store_true")
    br.add_argument("--allow-local", action="store_true")
    code = sub.add_parser("code", help="request opt-in AI patch proposal for explicitly selected source files")
    code.add_argument("--task", required=True)
    code.add_argument("--file", action="append", required=True)
    code.add_argument("--endpoint", required=True)
    code.add_argument("--model", required=True)
    code.add_argument("--project", type=Path, default=Path.cwd())
    code.add_argument("--allow-remote", action="store_true")
    code.add_argument("--apply", action="store_true")
    man = sub.add_parser("manifest", help="generate or verify SHA-256 integrity inventory (unsigned)")
    man.add_argument("--project", type=Path, default=Path.cwd())
    man.add_argument("--out", type=Path, default=Path('omniforge-manifest.json'))
    man.add_argument("--verify", action="store_true")
    rel = sub.add_parser("related", help="synonym-aware offline skill search")
    rel.add_argument("query"); rel.add_argument("--limit", type=int, default=5)
    pl = sub.add_parser("plan", help="reviewable offline skill workflow")
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
                     "mode": "core works locally without keys; optional code command uses BYOK endpoint"})
        elif args.action == "list":
            as_json(index())
        elif args.action == "search":
            if not 1 <= args.limit <= 20:
                raise ValueError("--limit must be 1..20")
            as_json(search_skills(args.query, limit=args.limit) if args.mode == "keyword" else
                    hybrid_search(args.query, limit=args.limit) if args.mode == "hybrid" else
                    embedding_search(args.query, model_path=args.model_path or "", limit=args.limit))
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
        elif args.action == "run":
            arguments = args.args[1:] if args.args and args.args[0] == "--" else args.args
            execution_plan = prepare_run(args.name, arguments, args.project,
                               docker=not args.unsafe_local, allow_network=args.allow_network,
                               timeout=args.timeout)
            as_json(execute_run(execution_plan, approve=args.approve))
        elif args.action == "orchestrate":
            as_json(execute_workflow(args.workflow, args.project, approve=args.approve,
                     unsafe_local=args.unsafe_local, allow_network=args.allow_network,
                     allow_commands=set(args.allow_command), workers=args.workers))
        elif args.action == "browser":
            as_json(browser_session(args.url, steps=load_actions(args.actions), project=args.project,
                                    screenshot=args.screenshot, approve=args.approve,
                                    allow_local=args.allow_local))
        elif args.action == "code":
            proposal = request_edits(args.task, args.project, args.file, endpoint=args.endpoint,
                                     model=args.model, allow_remote=args.allow_remote)
            as_json(apply_proposal(proposal, args.project, approve=args.apply))
        elif args.action == "manifest":
            if args.verify:
                as_json(check_manifest(args.project, args.out))
            else:
                manifest = build_manifest(args.project)
                args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                as_json({"created":str(args.out), "count": len(manifest["files"])})
        elif args.action == "related":
            as_json(related(args.query, limit=args.limit))
        elif args.action == "plan":
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
