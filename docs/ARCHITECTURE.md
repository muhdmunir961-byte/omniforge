# OmniForge architecture and security boundaries

OmniForge is a Python 3.11+ **tooling layer**, not an AI model or a self-hosted
general autonomous agent. Default behavior is offline, local-first and
non-executing until an operation is explicitly approved in the host CLI.

## Subsystems

| Module | Responsibility | Trust boundary |
| --- | --- | --- |
| `core.py`, `router.py`, `semantic.py` | Skill catalog, hybrid retrieval, optional local embeddings | Metadata is not a security endorsement |
| `cli.py` | User-facing arguments and explicit local approval | Host CLI actions may execute user-approved code |
| `mcp.py` | Read-only discovery, previews, provenance proof/verify/audit | AI client cannot approve live execution or browser actions |
| `runtime.py` | Docker-isolated skill execution by default | Docker kernel/daemon is outside the trust boundary; unsafe-local is unsandboxed |
| `agents.py` | Dependency-ordered workflow DAG and external approved executables | Allowlist is not a proof that another agent is safe |
| `browser.py` | Playwright browser actions on authorized sites | Application-level host checks are not full SSRF/DNS-rebinding isolation |
| `autocode.py` | BYOK selected-file source patch proposals | External model receives selected content; user approves edits |
| `provenance_v2*.py` | Strict local hash-chain, audit and optional unsigned EVM anchor | External trusted head required for full rewrite detection |
| `vscode-extension/` | VS Code UI for local CLI | Uses installed local CLI; extension is not a hosted service |

## Non-goals

OmniForge does not include model weights, 112 ready-to-use external integrations,
a wallet, seed-phrase management, automatic blockchain transactions, or a
guarantee of sandbox isolation against kernel compromise.

## Data flow

```text
User / local coding assistant
      |
      +--> CLI (explicit approval for execution)
      |       +--> local skill process in restricted Docker / optional unsafe host
      |       +--> selected-file code proposal --> review --> apply with backup
      |       +--> Playwright actions for authorized hosts
      |
      +--> MCP stdio
              +--> skill search / load / token budget
              +--> execution/browser preview only
              +--> provenance read-only verification

Local project --> SHA-256 snapshot --> ledger on disk
                      |                  |
                      |           external trusted checkpoint
                      +--> optional unsigned EVM tx --> external user wallet
```

## Release evidence

Separate workflows validate core tests on Windows/macOS/Linux, opt-in Linux
real integrations, package installation in a fresh environment, Python
vulnerability checks and CodeQL. Passing them demonstrates selected behavior
under those runner configurations, not general security certification.

See [SECURITY.md](../SECURITY.md), [release process](RELEASE_PROCESS.md),
and [v2 provenance guide](PROVENANCE_V2.ms.md).
