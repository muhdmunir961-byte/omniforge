"""Restore v1.0 CLI commands after applying an older reviewed v1.1 archive."""
from pathlib import Path

path = Path("src/omniforge/cli.py")
content = path.read_text(encoding="utf-8")


def replace_exact(before: str, after: str) -> None:
    global content
    if content.count(before) != 1:
        raise RuntimeError(f"Upgrade CLI mismatch: {before[:80]}")
    content = content.replace(before, after, 1)


replace_exact("from .semantic import hybrid_search, embedding_search",
              "from .semantic import hybrid_search, embedding_search\nfrom .planner import related, plan")
replace_exact('    sub.add_parser("mcp", help="start stdio MCP tool server")',
              '    rel = sub.add_parser("related", help="synonym-aware offline skill search")\n'
              '    rel.add_argument("query"); rel.add_argument("--limit", type=int, default=5)\n'
              '    pl = sub.add_parser("plan", help="reviewable offline skill workflow")\n'
              '    pl.add_argument("task"); pl.add_argument("--limit", type=int, default=3)\n'
              '    sub.add_parser("mcp", help="start stdio MCP tool server")')
replace_exact("            plan = prepare_run(args.name, arguments, args.project,",
              "            execution_plan = prepare_run(args.name, arguments, args.project,")
replace_exact("            as_json(execute_run(plan, approve=args.approve))",
              "            as_json(execute_run(execution_plan, approve=args.approve))")
replace_exact('        elif args.action == "mcp":',
              '        elif args.action == "related":\n'
              '            as_json(related(args.query, limit=args.limit))\n'
              '        elif args.action == "plan":\n'
              '            as_json(plan(args.task, limit=args.limit))\n'
              '        elif args.action == "mcp":')
path.write_text(content, encoding="utf-8")
print("Preserved CLI commands: related, plan")
