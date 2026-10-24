#!/usr/bin/env python3
"""Run installed OmniForge CLI in disposable projects and export a real preview.

Outputs: preview.html, preview.md, trace.json. No wallet keys, live EVM
transfers, external AI provider calls, or changes to the user's worktree.
"""
import argparse
import datetime
import html
import json
import os
from pathlib import Path
import subprocess
import tempfile


def execute(argv, *, expect=0, input_text=None):
    result = subprocess.run(
        argv, input=input_text, capture_output=True, text=True, timeout=40,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != expect:
        raise AssertionError(
            "Unexpected code " + str(result.returncode) + " expected " + str(expect)
            + " for " + repr(argv) + "\nstdout:\n" + result.stdout[-3000:]
            + "\nstderr:\n" + result.stderr[-3000:]
        )
    raw = result.stdout.strip()
    if input_text is not None:
        response = [json.loads(line) for line in raw.splitlines()]
    else:
        try:
            response = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            response = raw
    return response, {
        "command": " ".join(argv),
        "returncode": result.returncode,
        "stdout": result.stdout[:2000],
        "stderr": result.stderr[:900],
    }


def run_preview(output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    assertions = 0

    def call(label, args, *, expect=0, input_text=None):
        data, trace = execute(args, expect=expect, input_text=input_text)
        records.append({"label": label, **trace})
        return data

    def check(condition, label):
        nonlocal assertions
        assertions += 1
        if not condition:
            raise AssertionError("Preview check failed: " + label)

    with tempfile.TemporaryDirectory(prefix="omniforge-preview-") as dirname:
        root = Path(dirname)
        project = root / "project"
        project.mkdir()
        (project / "app.py").write_text("answer = 42\n")
        (project / "pyproject.toml").write_text('[project]\nname="demo"\nversion="0.0.1"\n')
        (project / ".env").write_text("DUMMY_PRIVATE=DO_NOT_PUBLISH\n")
        wallet = "0x" + "11" * 20

        version = call("CLI version", ["omniforge", "--version"])
        check("1.3.0" in version, "version")
        doc = call("Diagnostics", ["omniforge", "doctor"])
        check(doc["version"] == "1.3.0", "diagnostics")
        check(len(doc["skills"]) == 14, "14 bundled skills")
        all_skills = call("Bundled skills", ["omniforge", "list"])
        check(len(all_skills) == 14, "skill list")
        found = call("Hybrid search", ["omniforge", "search", "API errors"])
        check(isinstance(found, list) and bool(found), "hybrid search")
        related = call("Offline related search", ["omniforge", "related", "database"])
        check(isinstance(related, list) and bool(related), "related search")
        plan = call("Workflow plan", ["omniforge", "plan", "debug ESP32 firmware"])
        check(plan["mode"] == "dry-run", "plan is preview only")
        budget = call("Token estimate", ["omniforge", "budget", "--selected", "log-triage"])
        check(budget["skill_count"] == 14, "budget skill count")
        instructions = call("Lazy load SKILL.md", ["omniforge", "load", "log-triage"])
        check(instructions["name"] == "log-triage", "lazy skill load")
        inspect = call("Project detection", ["omniforge", "inspect", str(project)])
        check("python" in inspect["detected"], "Python project recognition")
        installed = call("Install skill", [
            "omniforge", "install", "log-triage", "--agent", "codex", "--project", str(project)
        ])
        check((Path(installed["installed"]) / "SKILL.md").is_file(), "installed skill")
        configured = call("VS Code setup", ["omniforge", "setup-vscode", "--project", str(project)])
        check(len(configured["written"]) > 0, "VS Code files")

        manifest = root / "manifest.json"
        made = call("SHA-256 manifest", [
            "omniforge", "manifest", "--project", str(project), "--out", str(manifest)
        ])
        check(made["count"] > 0, "manifest has files")
        valid_manifest = call("Verify manifest", [
            "omniforge", "manifest", "--project", str(project),
            "--out", str(manifest), "--verify"
        ])
        check(valid_manifest["ok"], "manifest correct")

        workflow = root / "workflow.json"
        workflow.write_text(json.dumps({"tasks": [
            {"id": "inspect", "kind": "skill", "skill": "python-symbols", "args": ["app.py"]},
            {"id": "review", "kind": "skill", "skill": "python-symbols",
             "args": ["app.py"], "depends_on": ["inspect"]},
        ]}))
        planned = call("DAG orchestration preview", [
            "omniforge", "orchestrate", str(workflow), "--project", str(project)
        ])
        check(planned["success"] and len(planned["tasks"]) == 2, "DAG preview")
        check(all(x["status"] == "preview-only" for x in planned["tasks"]),
              "no unapproved workflow execution")

        initialized = call("Initialize provenance v2", ["ofprov", "init", "--project", str(project)])
        check(initialized["version"] == 2, "v2 schema")
        first = call("Create snapshot", ["ofprov", "snapshot", "--project", str(project)])
        check(first["seq"] == 0, "genesis snapshot")
        good = call("Verify snapshot and trusted checkpoint", [
            "ofprov", "verify", "--project", str(project), "--check-files",
            "--expected-head", first["entry_hash"], "--expected-seq", "0"
        ])
        check(good["ok"] and good["trusted_checkpoint"], "trusted checkpoint verification")
        audit = call("Audit provenance policy", ["ofprov", "audit", "--project", str(project)])
        check(audit["ok"] and audit.get("snapshot_scope"), "audit scope")

        mcp_inputs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "preview", "version": "1"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "omniforge_provenance_verify",
                        "arguments": {"project": str(project), "check_files": True}}},
        ]
        mcp = call("Real MCP stdio session", ["omniforge", "mcp"],
                   input_text="\n".join(json.dumps(x) for x in mcp_inputs) + "\n")
        check(len(mcp) == 3, "MCP JSON-RPC framing")
        check(len(mcp[1]["result"]["tools"]) >= 10, "MCP tool discovery")
        response = json.loads(mcp[2]["result"]["content"][0]["text"])
        check(response["ok"], "real MCP verify")

        anchor = call("Unsigned EVM anchor preview", [
            "ofprov", "anchor", "--project", str(project), "--seq", "0",
            "--wallet", wallet, "--chain-id", "1337", "--prepare", "--ack-public-data"
        ])
        check(anchor["status"] == "wallet-approval-required", "no auto wallet approval")
        check(anchor["unsigned_transaction"]["data"] == "0x" + first["entry_hash"],
              "anchor calldata")
        call("Anchor consent enforced", [
            "ofprov", "anchor", "--project", str(project), "--wallet", wallet,
            "--chain-id", "1337", "--prepare"
        ], expect=2)

        (project / "app.py").write_text("answer = 43\n")
        tampered = call("Detect modified file", [
            "ofprov", "verify", "--project", str(project), "--check-files"
        ], expect=1)
        check(tampered["files"]["modified"] == ["app.py"], "tampered source detected")
        second = call("Append new snapshot", [
            "ofprov", "snapshot", "--project", str(project),
            "--expected-head", first["entry_hash"]
        ])
        check(second["seq"] == 1, "append snapshot")
        restored = call("Verify new snapshot", [
            "ofprov", "verify", "--project", str(project), "--check-files"
        ])
        check(restored["ok"], "current v2 snapshot")
        backup_dir = root / "exported-backup"
        backup = call("External backup + checkpoint", [
            "ofprov", "backup", "--project", str(project), "--out", str(backup_dir)
        ])
        check((backup_dir / "checkpoint.json").is_file(), "backup copied")
        check(backup["head"] == second["entry_hash"], "backup head")

        legacy = root / "legacy"
        legacy.mkdir()
        (legacy / "old.py").write_text("old_version=True\n")
        call("Legacy v1 record", [
            "omniforge", "blockchain", "record", "--project", str(legacy)
        ])
        old = (legacy / ".omniforge" / "chain.jsonl").read_bytes()
        migration_preview = call("v1 migration preview", [
            "ofprov", "migrate", "--project", str(legacy)
        ])
        check(migration_preview["status"] == "preview-only", "migration preview")
        migrated = call("v1 copy-only migration", [
            "ofprov", "migrate", "--project", str(legacy), "--approve"
        ])
        check(migrated["status"] == "migrated", "migration complete")
        check(old == (legacy / ".omniforge" / "chain.jsonl").read_bytes(),
              "old ledger untouched")
        call("Link legacy to v2 genesis", ["ofprov", "snapshot", "--project", str(legacy)])
        v1_current = call("Verify original v1 after migration", [
            "omniforge", "blockchain", "verify", "--project", str(legacy), "--check-current"
        ])
        check(v1_current["ok"], "v1 backward compatibility")
        v2_current = call("Verify migrated v2", [
            "ofprov", "verify", "--project", str(legacy), "--check-files"
        ])
        check(v2_current["ok"], "v2 forward compatibility")

        ledger_file = project / ".of-provenance" / "chain.jsonl"
        payload = ledger_file.read_text()
        original = '"anchor_status":"not_requested"'
        check(original in payload, "immutable status represented")
        ledger_file.write_text(payload.replace(original, '"anchor_status":"forged"', 1))
        invalid = call("Detect modified immutable ledger", [
            "ofprov", "verify", "--project", str(project)
        ], expect=1)
        check(invalid["ok"] is False, "ledger tampering is rejected")

    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    meta = {"result": "PASS", "version": "1.3.0", "utc": stamp,
            "cli_scenarios": len(records), "assertions": assertions,
            "details": "Installed wheel CLI; mock local projects only; no real wallets or third-party APIs"}
    (output / "trace.json").write_text(json.dumps({"meta": meta, "runs": records}, indent=2))
    lines = ["# OmniForge CLI Preview — Tested", "",
             "Source: installed wheel in disposable projects (not a mocked UI).", "",
             f"Status: **PASS** · {len(records)} executed commands · {assertions} assertions.", "",
             "| Scenario | Exit code | Result |", "| --- | ---: | --- |"]
    for item in records:
        lines.append("| " + item["label"] + " | " + str(item["returncode"]) + " | PASS |")
    for item in records:
        if item["label"] not in {
            "Diagnostics", "Hybrid search", "Create snapshot", "Real MCP stdio session",
            "Verify snapshot and trusted checkpoint", "Unsigned EVM anchor preview",
            "Detect modified file", "v1 copy-only migration", "Detect modified immutable ledger",
        }:
            continue
        lines.extend(["", "## " + item["label"], "", "~~~console",
                      "$ " + item["command"], item["stdout"][:900] or item["stderr"][:350],
                      "~~~"])
    (output / "preview.md").write_text("\n".join(lines) + "\n")
    parts = []
    for item in records:
        content = html.escape("$ " + item["command"] + "\n" +
                              (item["stdout"] or item["stderr"])[:1600])
        parts.append('<section class="row"><b>PASS</b><span>' +
                     html.escape(item["label"]) + '</span><pre>' + content + '</pre></section>')
    content = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>OmniForge — Tested CLI Preview</title>
<style>
:root{color-scheme:dark;font:15px/1.5 system-ui,sans-serif;background:#101418;color:#e7e5df}
body{max-width:1000px;margin:auto;padding:36px 24px 90px}
header{border-bottom:1px solid #384047;padding-bottom:36px;margin-bottom:32px}
h1{font-size:clamp(2rem,5vw,3.4rem);letter-spacing:-.05em}
p{color:#b3bbc3}.metrics{display:flex;gap:22px;flex-wrap:wrap}
.metrics div{padding:18px;border:1px solid #384047;border-radius:8px;min-width:120px}
.metrics strong{display:block;font-size:30px;color:#a4d8ac}
.row{padding:14px 18px;border:1px solid #394148;border-radius:9px;margin:12px 0;background:#171d22}
.row>b{font:11px monospace;color:#9dd0a6;margin-right:15px}
.row span{font-weight:600}.row pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:170px;overflow:auto;
margin:12px 0 0;border-top:1px solid #384047;padding-top:14px;color:#cbd4ca;font:12px/1.5 monospace}
</style><body><header><p>ENGINEERING / INTEGRATION PREVIEW</p>
<h1>OmniForge, actually tested.</h1>
<p>This report is generated from real CLI subprocesses using a packaged installation.</p>
<div class="metrics"><div><strong>""" + str(len(records)) + """</strong>commands</div>
<div><strong>""" + str(assertions) + """</strong>assertions</div>
<div><strong>PASS</strong>outcome</div></div></header>
<main>""" + "\n".join(parts) + """</main>
<footer><p>Generated """ + html.escape(stamp) + """. Optional real Docker, Chromium,
Anvil and VS Code host tests run in separate GitHub Actions jobs.</p></footer></body></html>"""
    (output / "preview.html").write_text(content)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("preview-output"))
    opts = parser.parse_args()
    run_preview(opts.out.resolve())
