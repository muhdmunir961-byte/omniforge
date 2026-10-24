# Changelog

## 1.3.1 — Cross-platform reliability and release readiness (2026-10-25)

- Added Linux/Windows/macOS CI for Python 3.11 and 3.13. Fixed actual Windows raw-byte hashing errors caused by OS text-mode CRLF/Control-Z conversion, and removed a Linux-only test assumption on macOS.
- Added CodeQL v4, pip-audit, redacted high-confidence secret-pattern scanning, Dependabot and measured branch-aware Python coverage.
- Added tested Python wheel/source/VSIX release-candidate pipeline with file-content checks, SHA-256 checksums, CycloneDX build-environment SBOM and version-tag-gated Sigstore attestation and GitHub Release.
- Added architecture and release-process guides, quickstart, CODEOWNERS and contributor issue/PR templates.
- Disabled HTTP redirects from BYOK model providers to prevent chosen source files and API credentials being forwarded to unintended destinations.
- Unit/branch coverage baseline was approximately 73% before additional regression tests. Security automation does not replace an independent penetration test.
- No public release, registry publication, Marketplace listing, external adoption, full provider-compatibility guarantee or security certification is claimed by this changelog alone.


## 1.3.0 — Strict OF-Provenance v2 and safe legacy migration (2026-10-25)

- Added new `ofprov` CLI and `omniforge provenance` subcommands without changing v1 `omniforge blockchain`.
- Implemented strict per-file SHA-256 snapshots with immutable full scan policy, domain-separated hashes, versioned schema and rejection of duplicate JSON keys, unexpected fields and unsafe paths.
- Added independent trusted head verification (`--expected-head` plus `--expected-seq`) to catch full ledger rewrites/rollbacks when the checkpoint is stored outside the mutable project.
- Added copy-only migration preserving byte-exact v1 JSONL/anchor backups, original v1 head and a linked v2 genesis. Excluded the v2 state from v1 manifests so legacy current-source verification remains compatible.
- Added filesystem limits, protected scan descriptors, change-during-read detection, writer locks, backup/export with checksums and a separate hash-linked RPC receipt journal that does not modify snapshot hashes.
- Added optional unsigned EVM anchor preparation requiring `--ack-public-data`; read-only RPC verification and optional local historic receipt journaling. No private keys or transaction broadcasting.
- Added read-only MCP v2 proof, verify and audit tools.
- Expanded Python security/migration/restore tests and real local EVM node tests, using the maintained Foundry toolchain Anvil v1.8.6 in GitHub CI.
- Added [audited Malay design and user documentation](docs/PROVENANCE_V2.ms.md) and [strict ledger schema](docs/PROVENANCE_V2_SCHEMA.json).
- Known limits: no independent blockchain consensus verification, cross-platform pen-testing or production mainnet validation; externally trusted checkpoints are necessary for full rewrite detection.


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
