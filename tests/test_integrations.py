"""Pure integration recipe tests; never launch optional untrusted applications."""
import json
import pytest
from omniforge import integrations

@pytest.mark.parametrize("client,field", [
 ("cline","mcpServers"), ("claude-code","mcpServers"),
 ("claude-desktop","mcpServers"), ("cursor","mcpServers"), ("vscode","servers"),
])
def test_valid_json_client_recipe(client,field):
    data=integrations.recipe(client,python="/usr/local/bin/python")
    assert data[field]["omniforge"]["args"] == ["-m","omniforge.mcp"]
    assert data[field]["omniforge"]["command"] == "/usr/local/bin/python"
    assert "blender" not in data[field]
    assert json.loads(integrations.stringify(data)) == data
    if client == "vscode":
        assert data["servers"]["omniforge"]["type"] == "stdio"

@pytest.mark.parametrize("client",integrations.CLIENTS)
def test_opt_in_blender_config_is_non_automatic(client):
    data=integrations.recipe(client,blender=True)
    servers=data["servers" if client=="vscode" else "mcpServers"]
    assert servers["blender"]["command"]=="uvx"
    assert servers["blender"]["args"]==["mcp-for-blender"]
    assert servers["blender"]["env"]["BLENDER_HOST"]=="127.0.0.1"
    assert servers["blender"]["env"]["BLENDER_MCP_SAFE_MODE"]=="1"
    assert "API_KEY" not in json.dumps(data)

@pytest.mark.parametrize("client",["unknown","","autocad","blender"])
def test_unknown_client_rejected(client):
    with pytest.raises(ValueError):
        integrations.recipe(client)

@pytest.mark.parametrize("path",["","hello\nbad","nul\x00evil"])
def test_unsafe_python_executable_rejected(path):
    with pytest.raises(ValueError):
        integrations.recipe("cline",python=path)

def test_unsupported_cad_apps_have_honest_status():
    info=integrations.inventory()
    assert info["apps"]["freecad"]["status"] == "unimplemented"
    assert info["apps"]["openscad"]["status"] == "unimplemented"
    assert info["apps"]["autocad"]["status"] == "unimplemented"
    doctor=integrations.doctor(True)
    assert doctor["blender_addon_handshake"] == "not_performed"
    assert doctor["third_party_tools_connected"] is False
