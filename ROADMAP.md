# OmniForge — Current Scope

OmniForge is a local-first capability layer for AI coding agents. This document describes what is available to users and what is not included in the current distribution.

## Available in v1.0.0

- Python 3.11+ CLI and 10 bundled script-backed skills.
- Metadata-based keyword routing and on-demand `SKILL.md` loading.
- MCP stdio tools: `omniforge_search`, `omniforge_load`, `omniforge_budget`.
- VS Code MCP configuration helper and project-local skill installation for Codex, Claude, Cursor, OpenCode, Copilot and Gemini.
- Local repo inspection, metadata validation and heuristic security audit.
- A reference catalog of 112 upstream repository candidates; none are bundled integrations.
- GitHub CI tests on Linux with Python 3.11, 3.12 and 3.13.

## Not included

- A hosted AI model, code-generation engine or autonomous multi-agent coordinator.
- Browsing, remote desktop, shell execution or deployment over MCP.
- Automatic execution of skill scripts; agents or users must invoke scripts separately.
- A security sandbox or comprehensive malware scanner.
- Verified integrations for the 112 candidate upstream repositories.
- A validated measurement of actual model billing tokens or improvements over other agents.
- Confirmed Windows or macOS compatibility.

## Usage

Follow the [README Quickstart](README.md#quickstart) to install and list skills.
Run `omniforge doctor`, `omniforge search "your task"`, or `omniforge setup-vscode --project .` from an environment with Python 3.11+.

Please file reproducible compatibility reports and issues on GitHub. See [SECURITY.md](SECURITY.md) for responsible disclosure.
