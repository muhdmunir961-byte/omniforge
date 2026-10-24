# OmniForge 1.1.1 audit

Date: 2026-10-24

## What the automated suite covers

- Existing CLI, ten original skills, installation guardrails, metadata router and MCP handshake.
- Local hybrid retrieval and missing-model behavior.
- Docker run preview, network restrictions and explicit unsandboxed execution.
- Workflow dependency validation, cycle rejection, approval and local execution.
- Browser URL/action validation and browser preview without real navigation.
- AI patch proposal validation, diff preview, backup-protected application, remote opt-in checks.
- File hash manifest detection of changed source.
- MCP execution/browser tools are **always preview-only**, even if a client passes `approve: true` or sets legacy environment flags.
- Regression tests cover symlinked write destinations for skill installation, VS Code setup, code-edit backups and browser screenshots.
- Optional skill adapter files and JavaScript extension syntax.

## Limitations and honest status

- A real Playwright Chromium session against a controlled localhost site was tested in GitHub Actions; third-party websites and authentication flows are not exhaustively validated.
- A real Docker sandbox was tested with `python:3.13-alpine`, read-only mounts, blocked networking, and owner UID/GID on Linux. This is functional integration evidence, not a formal sandbox security audit.
- Neural embedding retrieval requires the optional package and an already installed local model; offline fallback is hybrid text ranking.
- Actual external Trivy/KiCad/esptool commands require their respective executables and hardware/files.
- Model HTTP request/response, preview/apply and backup behavior were tested using a real HTTP connection to a controlled local OpenAI-compatible mock server. External providers and model quality remain unverified.
- VSIX packaging and VS Code Extension Development Host command activation/CLI output were tested on Linux; Marketplace publication and Windows/macOS editor compatibility remain unverified.
- Agent task coordinator is deterministic workflow execution, not autonomous iterative goal planning.
- SHA-256 inventory is **unsigned** and does not authenticate a maintainer identity.
- Existing upstream catalog of 112 tools is still candidate-only.

## Published source verification

- Python package version: **1.1.1**, published as source code on the repository default branch.
- Hardened upgrade published successfully by GitHub Actions run [40088583617](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40088583617).
- Post-publication CI run [40088762489](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40088762489): **64/64 tests passed** independently on Linux/Python 3.11, 3.12 and 3.13; native VS Code extension Node smoke passed.
- MCP tool requests cannot grant human approval; actual actions require an independently invoked local CLI `--approve` flag.
- Destination symlink checks mitigate accidental escapes, but do not prevent concurrent path-swap/TOCTOU attacks. Do not run on hostile worktrees while another process can mutate paths.
- These automated tests do not establish live Playwright compatibility, real Docker isolation, external API availability, full security certification or package registry publication.

## End-to-end verification, 24 October 2026

- Verified GitHub Actions run: [40100424908](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100424908).
- All four jobs passed: `docker-sandbox`, `browser-model`, `vscode-package`, `vscode-host`.
- The Docker private-directory read failure (`PermissionError: /workspace/sample.py`) was reproduced, fixed by using owner UID/GID in the container, then verified using real Docker execution.
- Browser interaction used a local HTTP page, Playwright Chromium, form entry, click and PNG screenshot.
- The model integration used a local OpenAI-compatible HTTP server, confirmed selected-file-only transmission, preview and approved source editing with backup.
- The VS Code integration launched an actual extension host, registered commands and displayed parsed CLI diagnostics; the VSIX package was built successfully.
- Linux only for these integrations; external models, hostile websites, Windows/macOS and formal penetration testing remain outside verified scope.
