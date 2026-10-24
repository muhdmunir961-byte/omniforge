"""Minimal MCP stdio JSON-RPC skill discovery bridge (no arbitrary execution)."""
from __future__ import annotations

import json
import sys
from typing import Any, TextIO
from . import __version__
from .core import bundled_names
from .router import search_skills, load_skill, token_report

PROTOCOL = "2025-06-18"
TOOLS = [
    {
        "name": "omniforge_search",
        "description": "Search available local agent skills by task. Returns compact metadata, not full instructions.",
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
                outcome = tool_result(search_skills(query, limit=limit))
            elif name == "omniforge_load":
                skill = args.get("name")
                if not isinstance(skill, str):
                    raise ValueError("name must be a string")
                outcome = tool_result(load_skill(skill))
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
