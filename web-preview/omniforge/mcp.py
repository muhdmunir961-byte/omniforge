"""Minimal MCP stdio JSON-RPC skill discovery bridge (no arbitrary execution)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO
from . import __version__
from .core import bundled_names
from .router import search_skills, load_skill, token_report
from .semantic import hybrid_search
from .runtime import prepare_run, execute_run
from .browser import browser_session
from .blockchain import verify as verify_provenance_chain, proof as read_provenance_block
from . import provenance_v2 as provenance2

PROTOCOL = "2025-06-18"
TOOLS = [
    {
        "name": "omniforge_search",
        "description": "Search local agent skills with hybrid local text ranking. Returns metadata only.",
        "inputSchema": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Short task description"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}
        }, "required": ["query"]},
    },
    {
        "name": "omniforge_load",
        "description": "Load the full SKILL.md for one explicitly selected skill, on demand.",
        "inputSchema": {"type": "object", "properties": {
            "name": {"type": "string"}
        }, "required": ["name"]},
    },
    {
        "name": "omniforge_run",
        "description": "Preview a bundled skill execution. Execution is disabled via MCP; use the local CLI for manually approved actions.",
        "inputSchema": {"type":"object","properties":{
            "name":{"type":"string"}, "args":{"type":"array","items":{"type":"string"}},
            "project":{"type":"string"}
        },"required":["name","project"]},
    },
    {
        "name": "omniforge_browser",
        "description": "Preview a browser navigation. Navigation is disabled via MCP; use the local CLI for manually approved actions.",
        "inputSchema":{"type":"object","properties":{
            "url":{"type":"string"}, "project":{"type":"string"},
            
        },"required":["url","project"]},
    },
    {
        "name": "omniforge_chain_verify",
        "description": "Read-only verification of a local OmniForge blockchain provenance ledger and optional current project snapshot.",
        "inputSchema": {"type": "object", "properties": {
            "project": {"type": "string"},
            "check_current": {"type": "boolean", "default": False}
        }, "required": ["project"]},
    },
    {
        "name": "omniforge_chain_proof",
        "description": "Read-only access to one previously recorded local provenance block hash. No wallet or network access.",
        "inputSchema": {"type": "object", "properties": {
            "project": {"type": "string"}, "height": {"type": "integer", "minimum": 0}
        }, "required": ["project"]},
    },
    {
        "name": "omniforge_provenance_verify",
        "description": "Read-only strict v2 project hash-chain verification; supports an externally trusted checkpoint.",
        "inputSchema": {"type": "object", "properties": {
            "project": {"type": "string"},
            "check_files": {"type": "boolean", "default": False},
            "expected_head": {"type": "string"},
            "expected_seq": {"type": "integer", "minimum": 0}
        }, "required": ["project"]},
    },
    {
        "name": "omniforge_provenance_proof",
        "description": "Read one validated immutable v2 project snapshot. No wallet/signing/network access.",
        "inputSchema": {"type": "object", "properties": {
            "project": {"type": "string"},
            "seq": {"type": "integer", "minimum": 0}
        }, "required": ["project"]},
    },
    {
        "name": "omniforge_provenance_audit",
        "description": "Read-only v2 audit: local chain, files, policy history and privacy warnings.",
        "inputSchema": {"type": "object", "properties": {
            "project": {"type": "string"},
            "expected_head": {"type": "string"},
            "expected_seq": {"type": "integer", "minimum": 0}
        }, "required": ["project"]},
    },
    {
        "name": "omniforge_budget",
        "description": "Estimate skill context overhead for lazy-loading versus all-at-once loading.",
        "inputSchema": {"type": "object", "properties": {
            "selected": {"type": "string", "description": "Optional selected bundled skill"}
        }},
    },
]


def tool_result(payload: Any, *, error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": error}


def dispatch(message: dict) -> dict | None:
    """Handle protocol requests. Notifications are intentionally silent."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request"}}
    if "id" not in message:
        return None
    ident = message["id"]
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": "Invalid params"}}
    try:
        if method == "initialize":
            outcome = {"protocolVersion": PROTOCOL,
                       "capabilities": {"tools": {"listChanged": False}},
                       "serverInfo": {"name": "omniforge", "version": __version__}}
        elif method == "ping":
            outcome = {}
        elif method == "tools/list":
            outcome = {"tools": TOOLS}
        elif method == "tools/call":
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            name = params.get("name")
            if name == "omniforge_search":
                query = args.get("query")
                if not isinstance(query, str):
                    raise ValueError("query must be a string")
                limit = args.get("limit", 5)
                if type(limit) is not int or not 1 <= limit <= 20:
                    raise ValueError("limit must be between 1 and 20")
                outcome = tool_result(hybrid_search(query, limit=limit))
            elif name == "omniforge_load":
                skill = args.get("name")
                if not isinstance(skill, str):
                    raise ValueError("name must be a string")
                outcome = tool_result(load_skill(skill))
            elif name == "omniforge_run":
                name_arg, project = args.get("name"), args.get("project")
                argv = args.get("args", [])
                if not isinstance(name_arg,str) or not isinstance(project,str) or not isinstance(argv,list) or not all(isinstance(a,str) for a in argv):
                    raise ValueError("name, project and args must be valid")
                plan = prepare_run(name_arg, argv, Path(project), docker=True)
                outcome = tool_result(execute_run(plan, approve=False))
            elif name == "omniforge_browser":
                url, project = args.get("url"), args.get("project")
                if not isinstance(url,str) or not isinstance(project,str):
                    raise ValueError("url and project must be strings")
                outcome = tool_result(browser_session(url,project=Path(project),approve=False))
            elif name == "omniforge_chain_verify":
                project, current = args.get("project"), args.get("check_current", False)
                if not isinstance(project, str) or type(current) is not bool:
                    raise ValueError("project must be a string and check_current a boolean")
                outcome = tool_result(verify_provenance_chain(Path(project), check_current=current))
            elif name == "omniforge_chain_proof":
                project, height = args.get("project"), args.get("height")
                if not isinstance(project, str) or (height is not None and
                   (type(height) is not int or height < 0)):
                    raise ValueError("project must be a string and height must be a nonnegative integer")
                outcome = tool_result(read_provenance_block(Path(project), height))
            elif name in ("omniforge_provenance_verify",
                              "omniforge_provenance_audit",
                              "omniforge_provenance_proof"):
                project = args.get("project")
                if not isinstance(project, str):
                    raise ValueError("project must be a string")
                if name == "omniforge_provenance_proof":
                    seq = args.get("seq")
                    if seq is not None and (type(seq) is not int or seq < 0):
                        raise ValueError("seq must be a nonnegative integer")
                    outcome = tool_result(provenance2.proof(Path(project), seq))
                else:
                    head, seq = args.get("expected_head"), args.get("expected_seq")
                    if (head is not None and not isinstance(head, str)
                        or seq is not None and (type(seq) is not int or seq < 0)):
                        raise ValueError("Invalid trusted checkpoint")
                    if name == "omniforge_provenance_verify":
                        check = args.get("check_files", False)
                        if type(check) is not bool:
                            raise ValueError("check_files must be boolean")
                        outcome = tool_result(provenance2.verify(
                            Path(project), check_files=check,
                            expected_head=head, expected_seq=seq))
                    else:
                        outcome = tool_result(provenance2.audit(
                            Path(project), expected_head=head, expected_seq=seq))
            elif name == "omniforge_budget":
                selected = args.get("selected")
                if selected is not None and not isinstance(selected, str):
                    raise ValueError("selected must be a string")
                outcome = tool_result(token_report(chosen=selected))
            else:
                outcome = tool_result({"error": f"Unknown tool {name}"}, error=True)
        else:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "Method not found"}}
        return {"jsonrpc": "2.0", "id": ident, "result": outcome}
    except (ValueError, OSError) as exc:
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": ident, "result": tool_result({"error": str(exc)}, error=True)}
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": str(exc)}}


def serve(input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> None:
    input_stream = input_stream if input_stream is not None else sys.stdin
    output_stream = output_stream if output_stream is not None else sys.stdout
    for line in input_stream:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = dispatch(request)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if response is not None:
            output_stream.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            output_stream.flush()

if __name__ == "__main__":
    serve()
