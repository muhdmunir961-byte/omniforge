# OmniForge — Scope and compatibility

This document describes capability boundaries, not growth milestones.

## Implemented in source

- CLI, lazy skill registry, metadata search and optional local embedding lookup.
- 14 bundled skill packages: ten original operational Python scripts and four optional upstream adapters.
- MCP stdio discovery and opt-in gated run/browser functionality.
- Preview-first Docker script execution and approved external-agent task workflow coordination.
- Opt-in Playwright browser actions, optional OpenAI-compatible code-edit suggestions and backup-protected application.
- Local SHA-256 inventory/verification.
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
