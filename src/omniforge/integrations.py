"""MCP client configuration recipes. Only JSON generation; no execution or installation.

The Blender MCP adapter is third-party, not bundled or verified by OmniForge.
Other CAD packages are explicitly marked unsupported pending real adapters.
"""
import json
import shutil
import sys

CLIENTS = ("cline", "claude-code", "claude-desktop", "cursor", "vscode")
APPLICATIONS = {
    "blender": {"status": "third-party-opt-in", "repo": "https://github.com/ahujasid/mcp-for-blender"},
    "threejs": {"status": "via-coding-agent", "hint": "React Three Fiber / Three.js source editing"},
    "freecad": {"status": "unimplemented", "hint": "Needs an independently vetted local MCP adapter"},
    "openscad": {"status": "unimplemented", "hint": "No native MCP adapter bundled"},
    "autocad": {"status": "unimplemented", "hint": "Requires separate local licensed app and adapter"},
}
def recipe(client, *, blender=False, python=None):
    if client not in CLIENTS:
        raise ValueError("Unsupported MCP client")
    interpreter = sys.executable if python is None else python
    if not interpreter or any(c in interpreter for c in "\n\r\x00"):
        raise ValueError("Invalid interpreter")
    servers = {"omniforge": {"command": interpreter, "args": ["-m", "omniforge.mcp"]}}
    if blender:
        servers["blender"] = {
            "command": "uvx",
            "args": ["mcp-for-blender"],
            "env": {
                "BLENDER_HOST": "127.0.0.1",
                "BLENDER_PORT": "9876",
                "BLENDER_MCP_SAFE_MODE": "1",
            },
        }
    if client == "vscode":
        return {"servers": {k: {"type": "stdio", **v} for k, v in servers.items()}}
    return {"mcpServers": servers}

def inventory():
    return {
        "clients": list(CLIENTS),
        "bundled": {"omniforge": "10 read-only/preview MCP tools; local stdio"},
        "apps": APPLICATIONS,
        "byok": "OpenAI-compatible chat completions, selected-file proposal, user-approved apply",
        "note": "Models, MCP tools and CAD apps are distinct layers; no autonomous universal bridge is claimed",
    }

def doctor(blender=False):
    return {"python": sys.executable, "omniforge_cli": bool(shutil.which("omniforge")),
            "uvx_installed": bool(shutil.which("uvx")),
            "blender_binary_installed": bool(shutil.which("blender")),
            "blender_requested": bool(blender),
            "blender_addon_handshake": "not_performed",
            "third_party_tools_connected": False}

def stringify(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False)
