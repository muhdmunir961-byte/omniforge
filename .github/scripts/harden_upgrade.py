"""Fail-closed security patch for the reviewed OmniForge upgrade bundle.

Run ONLY after archive integrity/path verification, and before CI/tests.
"""
from pathlib import Path


def patch(path: str, changes: list[tuple[str, str]]) -> None:
    target = Path(path)
    content = target.read_text(encoding="utf-8")
    for before, after in changes:
        if content.count(before) != 1:
            raise RuntimeError(f"Unexpected upgrade source: {path} (matches={content.count(before)})")
        content = content.replace(before, after, 1)
    target.write_text(content, encoding="utf-8")


# MCP clients may request execution but cannot approve it on a human's behalf.
patch("src/omniforge/mcp.py", [
    ("Real execution requires host-enabled OMNIFORGE_MCP_EXECUTION=1, Docker isolation, and approval.",
     "Execution is disabled via MCP; use the local CLI for manually approved actions."),
    ("Real navigation requires OMNIFORGE_MCP_BROWSER=1 on the host and approval.",
     "Navigation is disabled via MCP; use the local CLI for manually approved actions."),
    ('"project":{"type":"string"}, "approve":{"type":"boolean","default":False}',
     '"project":{"type":"string"}'),
    ('"approve":{"type":"boolean","default":False}\n        }', '\n        }'),
    ('                permitted = os.environ.get("OMNIFORGE_MCP_EXECUTION") == "1"\n'
     '                outcome = tool_result(execute_run(plan, approve=permitted and args.get("approve") is True))',
     '                outcome = tool_result(execute_run(plan, approve=False))'),
    ('                permitted = os.environ.get("OMNIFORGE_MCP_BROWSER") == "1"\n'
     '                outcome = tool_result(browser_session(url,project=Path(project),\n'
     '                         approve=permitted and args.get("approve") is True))',
     '                outcome = tool_result(browser_session(url,project=Path(project),approve=False))'),
])

patch("src/omniforge/autocode.py", [
    ("from urllib.request import Request, urlopen",
     "from urllib.request import Request, urlopen\nfrom .core import secure_project_path"),
    ("        p = (project / name).resolve()", "        p = secure_project_path(project, name)"),
    ("        target = (root / edit['path']).resolve()",
     "        target = secure_project_path(root, edit['path'])"),
    ("    backup_root = root / '.omniforge' / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')",
     "    backup_root = secure_project_path(root, '.omniforge', 'backups', datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))"),
])

patch("src/omniforge/browser.py", [
    ("from urllib.parse import urlparse",
     "from urllib.parse import urlparse\nfrom .core import secure_project_path"),
    ("        requested = root / screenshot\n        shot = requested.resolve()",
     "        shot = secure_project_path(root, screenshot)"),
])

if "def secure_project_path(" not in Path("src/omniforge/core.py").read_text(encoding="utf-8"):
    raise RuntimeError("Core symlink protection must be in place before this upgrade")
print("Upgrade security patch applied")
