# OmniForge 3D, CAD, MCP clients and OpenAI-compatible BYOK

## Compatibility as shipped

| Workflow | Supported today | Limitation |
|---|---|---|
| Build interactive 3D website | Use Cline/Claude Code with Three.js or React Three Fiber sources | OmniForge is a local skill/MCP helper, not a full rendered 3D editor |
| Connect OmniForge to Cline/Claude | Local stdio MCP configuration | Only 10 read-only/preview OmniForge tools; no autonomous execution via MCP |
| Blender modelling via AI tools | Generate optional config for external mcp-for-blender server | Requires Blender + addon + uvx, started and approved locally; third-party |
| FreeCAD, AutoCAD, OpenSCAD | Advisory guidance only | No built-in MCP bridge, proprietary CAD operations or format conversion |
| OpenAI-compatible BYOK | Selected-file code proposals via chat completions | No universal live agent orchestration; edits are reviewed before apply |

## Actual CLI setup (copy output to the client configuration)

```bash
python -m pip install -e .
omniforge integrations list
omniforge integrations doctor --blender
omniforge integrations config --client cline --blender
omniforge integrations config --client claude-code --blender
omniforge integrations config --client vscode --blender
```

Each command produces JSON only; **nothing is installed, no settings are changed, no third-party tools are executed**.
Copy the generated JSON into each client's MCP settings and merge it with existing servers.
Cline, Claude Code and Claude Desktop use an `mcpServers` object. Native VS Code uses a `servers` object with `type: stdio`.
Check client versions before use, as configuration schemas can change.

Blender reference: https://github.com/ahujasid/mcp-for-blender
Cline reference: https://github.com/cline/cline/blob/main/docs/mcp/mcp-overview.mdx

## Blender setup

1. Install Blender and the external Blender MCP addon from the provider's verified repository.
2. Install uv/uvx and follow its current setup steps (such as `uvx mcp-for-blender setup`).
3. Start the local Blender addon server, on loopback (`127.0.0.1`, default `9876`).
4. Copy the generated OmniForge + Blender MCP configuration into Cline or Claude Code.
5. Restart the client's MCP connection and verify Blender tools appear separately from OmniForge tools.
6. Test with a disposable .blend file first; inspect generated Python scripts before running.

Generated config requests `BLENDER_MCP_SAFE_MODE=1`, but this does not guarantee total isolation.
Blender addons can modify a scene, filesystem or host environment. Never expose Blender's socket publicly.
OmniForge does not currently proxy Blender MCP through its own ten MCP tools.

## 3D websites

Use ordinary coding agents (Cline/Claude Code) to write Three.js, React Three Fiber or WebGL code.
Create models in Blender, then export glTF/GLB, review file sizes, mobile frame rate, lighting and loading fallbacks.
Automated asset generation/geometry verification and running Blender inside Vercel are **not** included.

## BYOK with OpenAI-compatible model

```bash
export OMNIFORGE_API_KEY='YOUR_PROVIDER_KEY'
omniforge code --project ./my-website --file src/App.tsx \
  --task 'Add a reviewable Three.js canvas component' \
  --endpoint https://YOUR_PROVIDER/v1/chat/completions --model YOUR_MODEL --allow-remote
```

The first call returns a diff proposal, not an unconditional change. Repeat only with `--apply` after review.
Only selected source files are sent to the remote provider; HTTPS is required outside loopback.
Provider redirects are blocked and changes are protected with original SHA-256 and backups.
**Provider API (text generation) and MCP tool server (action interface) are separate protocols.**
Model BYOK credentials belong in local environment variables, never GitHub or MCP JSON.

## Other modelling software

FreeCAD is a practical alternative for dimensioned parametric mechanical designs; OpenSCAD is useful for script-based CAD.
AutoCAD integration needs an independently reviewed, compatible extension and local licensing.
OmniForge must not claim verified integration with these apps without application E2E tests.

## Maintainer verification

```bash
python -m pytest -q tests/test_integrations.py
omniforge integrations config --client cline --blender
omniforge integrations doctor --blender
```

Passing configuration tests proves generated JSON shape, not successful 3D scene automation.
