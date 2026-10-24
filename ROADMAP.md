# OmniForge — Scope and compatibility

This document describes capability boundaries, not growth milestones.

## Implemented in source

- CLI, lazy skill registry, metadata search and optional local embedding lookup.
- 14 bundled skill packages: ten original operational Python scripts and four optional upstream adapters.
- MCP stdio discovery, skill loading and **preview-only** run/browser planning; live actions are available only through the separately invoked local CLI.
- Preview-first Docker script execution and approved external-agent task workflow coordination.
- Opt-in Playwright browser actions, optional OpenAI-compatible code-edit suggestions and backup-protected application.
- Local SHA-256 inventory/verification.
- Local hash-chain provenance and optional Ethereum-compatible transaction anchoring/verification, with user-signed transactions (no wallet custody).
- VS Code MCP configuration and experimental local VS Code extension source.

## Boundaries

- No model is bundled or hosted.
- External agent and browser installations are prerequisites; their end-to-end interoperability varies.
- No automatic multi-step autonomous code-fixing loop or provider-independent cost accounting.
- Local hybrid text ranking is not a neural embedding model; optional embeddings must be supplied locally.
- Docker isolation is available only when Docker is installed and explicitly approved. It is not a substitute for a hardened virtual machine.
- The 112 GitHub catalog entries remain candidates; upstream source is not vendored.
- No cryptographic release signature and no published VS Code Marketplace extension.

For supported commands and real usage examples, read [README.md](README.md).

## Completed: strict OF-Provenance v2 (OmniForge 1.3.0)

- Strict immutable snapshot records with full file hashes and versioned policy objects.
- Explicit v1 copy-only migration retaining original hashes and optional anchor metadata.
- Independently trusted checkpoint checks, backup and controlled manual restoration procedures.
- Separate local receipt journal with hash links and explicit RPC re-verification caveats.
- Maintained local EVM test node through Foundry; no signing or broadcasting functionality in application.
- Dedicated v2 CLI and read-only MCP interface, keeping v1 legacy commands working.

### Still requiring independent verification

- Windows/macOS hostile-filesystem race tests and external penetration testing.
- Actual public RPC-provider diversity, chain reorg monitoring and public-network verification.
- End-to-end package lock hashes, SBOM and ongoing supply-chain review.
