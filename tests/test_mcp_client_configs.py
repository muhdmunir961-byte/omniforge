"""Real stdio MCP handshake using each exported client recipe.

This tests the process/JSON-RPC contract, not just syntactically valid JSON.
Optional Blender/FreeCAD adapters are NEVER executed in CI.
"""
import json
import subprocess
from omniforge.integrations import CLIENTS, recipe
import pytest


@pytest.mark.parametrize("client", CLIENTS)
def test_client_recipe_launches_real_mcp_server(client):
    config=recipe(client)
    servers=config["servers" if client=="vscode" else "mcpServers"]
    settings=servers["omniforge"]
    command=[settings["command"], *settings["args"]]
    requests=[
        {"jsonrpc":"2.0","id":1,"method":"initialize",
         "params":{"protocolVersion":"2025-06-18","capabilities":{},
                   "clientInfo":{"name":"omniforge-recipe-test","version":"1.0"}}},
        {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}},
        {"jsonrpc":"2.0","id":3,"method":"tools/call",
         "params":{"name":"omniforge_load","arguments":{"name":"realtime-3d-mesh"}}},
    ]
    proc=subprocess.run(command,input="\n".join(map(json.dumps,requests))+"\n",
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                        timeout=12,check=False)
    assert proc.returncode==0,proc.stderr[-1200:]
    messages=[json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert len(messages)==3,(messages,proc.stderr[-1200:])
    assert messages[0]["result"]["serverInfo"]["name"]=="omniforge"
    names={tool["name"] for tool in messages[1]["result"]["tools"]}
    assert "omniforge_search" in names
    assert "omniforge_load" in names
    assert "omniforge_provenance_verify" in names
    assert len(names)>=10
    assert not messages[2]["result"]["isError"], messages[2]
    assert "realtime-3d-mesh" in messages[2]["result"]["content"][0]["text"]
