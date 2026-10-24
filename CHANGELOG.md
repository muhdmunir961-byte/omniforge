# Changelog

## 1.2.0 — Blockchain provenance and EVM anchoring (2026-10-24)

- Added SHA-256 local hash-chain ledger and source snapshot verification.
- Added blockchain CLI commands: record, verify, proof, anchor and verify-anchor.
- Added unsigned EVM zero-value self-transaction payload generation; wallet signs and broadcasts independently.
- Added read-only RPC verifier for chain ID, wallet, calldata, receipt status, hash and confirmations.
- Added tamper, truncation, symlink, concurrency, wrong chain and RPC tests.
- Verified actual EVM anchoring using a disposable local Ganache chain in CI.
- Published guide and English / Indonesian / Malay README documentation.
- Local ledger is not decentralized consensus; public network gas and user's wallet are required for anchoring.


## 1.1.1 — Integration verification and Docker permissions fix (2026-10-24)

- Fixed Docker sandbox access for private user-owned project directories by running with the invoking UID/GID rather than root with dropped capabilities.
- Added real Chromium browser interaction, screenshot, local model HTTP, and Docker isolated execution plus DAG workflow tests.
- Added real VS Code Extension Development Host test and VSIX packaging check on Linux.
- Added opt-in E2E GitHub Actions workflow alongside the existing three-version Python unit-test matrix.
- Confirmed user-controlled approval and retained read-only Docker mounts and network-disabled default.
- Limitations remain for real third-party APIs, unaudited websites, and non-Linux environments.

## 1.1.0 — Capability extension (2026-10-24)

- Added metadata hybrid search and optional *offline* neural embedding search.
- Added Docker-based, opt-in bundled script runner with preview default and limited host fallback.
- Added dependency-ordered task runner for bounded skill workflows and explicitly allowlisted external agent CLIs.
- Added opt-in Playwright website actions and remote-model-assisted code patch proposals with SHA-256 checks and backups.
- Added an experimental local VS Code extension (source, not Marketplace published).
- Added Trivy, KiCad CLI, esptool and Playwright adapter skill packages; actual upstream dependencies remain optional.
- Expanded MCP to five tools; execution and browser MCP endpoints are **preview-only** and cannot use model-supplied approval.
- Added unsigned local SHA-256 manifests.
- Kept existing v1.0 commands and 112 unverified catalog candidates.
- Hardened skill installation, VS Code configuration, AI patch backups and screenshot destinations against symlink traversal.

## 1.0.0 — Initial core release (2026-10-24)

- Python CLI, 10 original bundled script skills, lazy metadata routing and JSON-RPC stdio MCP server.
- VS Code setup and six coding-agent install targets plus universal.
- Tests passed on Linux/Python 3.11, 3.12 and 3.13.
