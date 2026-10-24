# Changelog

## 1.1.0 — Capability extension (2026-10-24)

- Added metadata hybrid search and optional *offline* neural embedding search.
- Added Docker-based, opt-in bundled script runner with preview default and limited host fallback.
- Added dependency-ordered task runner for bounded skill workflows and explicitly allowlisted external agent CLIs.
- Added opt-in Playwright website actions and remote-model-assisted code patch proposals with SHA-256 checks and backups.
- Added an experimental local VS Code extension (source, not Marketplace published).
- Added Trivy, KiCad CLI, esptool and Playwright adapter skill packages; actual upstream dependencies remain optional.
- Expanded MCP to five tools with disabled-by-default execution and browser capabilities.
- Added unsigned local SHA-256 manifests.
- Kept existing v1.0 commands and 112 unverified catalog candidates.

## 1.0.0 — Initial core release (2026-10-24)

- Python CLI, 10 original bundled script skills, lazy metadata routing and JSON-RPC stdio MCP server.
- VS Code setup and six coding-agent install targets plus universal.
- Tests passed on Linux/Python 3.11, 3.12 and 3.13.
