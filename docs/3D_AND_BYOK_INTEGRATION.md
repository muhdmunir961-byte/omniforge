# OmniForge: Cline, Claude Code, Blender, FreeCAD, AutoCAD and BYOK

These are verified-format integration examples, **not a bundled Blender/AutoCAD bridge**.
The public Vercel terminal intentionally does not launch arbitrary external MCP processes.

## Real architecture

An MCP-capable coding assistant is the HOST, while OmniForge and 3D add-ons are independent MCP servers.
The host chooses the AI model, obtains tool permissions and dispatches calls:

    Cline or Claude Code
      |-- selected model (Cline's BYOK provider settings)
      |-- OmniForge MCP (skills, previews, integrity checks)
      |-- Blender MCP (Blender addon running on localhost)
      |-- FreeCAD MCP (FreeCAD addon running on localhost)
      +-- local React/Next.js, Three.js or React Three Fiber project

## Cline

First install OmniForge locally from this repo with:

    python -m pip install -e .
    omniforge --version

Open Cline > MCP Servers > Configure MCP Servers and adapt the JSON in
examples/mcp/cline-3d.json. OmniForge is enabled; Blender and FreeCAD are
deliberately disabled until their apps and community add-ons are installed.
Cline reads command/args and env for a local stdio server. Configure AI
model selection and BYOK credentials separately in Cline itself.
Never put keys in tracked JSON. Disable automatic approval of write/code tools.

## Claude Code

Use examples/mcp/claude-code-3d.mcp.json as an example for a project .mcp.json.
Alternatively, register the local servers using:

    claude mcp add omniforge -- omniforge mcp
    claude mcp add blender -- uvx blender-mcp
    claude mcp list

Claude Code model authentication is NOT automatically OpenAI-compatible BYOK.
OmniForge's BYOK patch editor is a separate command, not Claude Code's LLM.

## Blender MCP

Community bridge: https://github.com/ahujasid/blender-mcp
Install Blender, the documented addon and the uv/uvx tool. Start the addon
connection in the 3D View panel. The community server typically connects to
Blender at 127.0.0.1:9876; do not expose it to the public internet.
Tools can inspect scenes, make meshes/materials, render and run Python
inside Blender. Arbitrary Blender Python is risky; save copies and obtain
human approval for any code execution or destructive write.
Disable optional telemetry when privacy requirements demand it.
OmniForge does not automatically proxy or authorize Blender MCP tools today.

## FreeCAD MCP

Community bridge: https://github.com/neka-nat/freecad-mcp
Install the FreeCAD addon, launch its local RPC server, then configure
uvx freecad-mcp as a separate MCP server. Start with a disposable model.
For engineering CAD, retain parametric geometry and dimension units. Use
appropriate conversions for STEP/STL/GLB; do not claim perfect DWG fidelity.

## AutoCAD and Civil 3D (important limitation)

Autodesk's Oct 23, 2026 support article states its AutoCAD/Civil 3D
local MCP Tech Preview runs in Autodesk Assistant and AUTODESK ASSISTANT
is the only officially supported AI client for that particular server:
https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/AutoCAD-Civil-3D-MCP.html

Therefore it must NOT be advertised as a verified Cline/Claude Code/OmniForge
bridge. Alternative engineering paths include a separately developed desktop
AutoCAD .NET/ObjectARX/COM plugin with explicit approval, or Autodesk Platform
Services cloud Automation API with authentication and licensing.
Source: https://aps.autodesk.com/developer/overview/automation-api

## Building a true interactive 3D website

1. Load interface-craft, motion-interaction, realtime-3d-mesh, visual-qa skills
   from the installed local OmniForge MCP through the selected coding host.
2. Use Three.js or React Three Fiber for actual vertices/materials/cameras;
   CSS perspective alone is not an interactive 3D scene.
3. Generate a genuine test OBJ using the bundled realtime-3d-mesh script.
   The built-in generator supports torus and UV sphere, not full CAD design.
4. Create or import owned/licensed glTF/GLB assets in Blender/FreeCAD as needed.
5. Confirm orbit, pinch, camera reset, accessibility, mobile GPU budget,
   file sizes, and real screenshot results before deploying.

## BYOK OpenAI-compatible support today

OmniForge has a SINGLE-PASS patch editor: it sends up to five selected source
files to the configured Chat Completions endpoint. Remote calls require
HTTPS and --allow-remote; the model must return an expected JSON edit object.
Original file SHA-256 and human-reviewed --apply protect source changes.
No API keys should be committed; provide OMNIFORGE_API_KEY locally.

Example in a trusted project with src/App.tsx already present:

    omniforge code --task "Improve the 3D viewer usability" \
      --file src/App.tsx \
      --endpoint https://YOUR-PROVIDER.example/v1/chat/completions \
      --model YOUR_SUPPORTED_CHAT_MODEL --allow-remote

Only add --apply AFTER reviewing the returned diff. The endpoint and model
must actually implement compatible Chat Completions and JSON content output.
This is not a universal assistant, token meter, persistent model router or
tool-calling MCP client. BYOK and MCP are independent, complementary layers.

## What is still missing for a universal 3D/BYOK platform

- General MCP client/registry/connect-disconnect and permissioned tool proxy.
- Verified live Blender and FreeCAD integration E2E against installed apps.
- Optional Autodesk plugin/client implementation with version/license gates.
- Multiple BYOK profiles, encrypted secret storage, tool-call loop, limits.
- Multi-file 3D scene workspace, safe previews and human approval surfaces.

## Verify installed integration

    omniforge doctor
    omniforge search "WebGL interactive 3D viewer"
    omniforge load realtime-3d-mesh
    omniforge mcp

Run the last command via your assistant's stdio MCP config, not as a normal
interactive shell. In the assistant, check tools/list and load one known skill.
Third-party Blender and FreeCAD must be started independently first.
