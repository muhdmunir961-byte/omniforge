<div align="center">

# OmniForge

**Local-first skills, tools and permissioned workflows for AI coding assistants.**

Python 3.11+ · MCP (stdio) · VS Code · MIT

**Languages:** **English** · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md)

</div>

OmniForge is a companion to coding assistants such as Codex, Claude Code, Cursor, OpenCode and Gemini. It does **not** bundle a model or replace an AI coding agent. Its default operation is local, with explicit opt-in for external model APIs and browser/network access.

## Install

```bash
git clone https://github.com/muhdmunir961-byte/omniforge.git
cd omniforge
python -m pip install -e .
omniforge doctor
omniforge list
omniforge search "debug ESP32 errors"
```

For development: `python -m pip install pytest && python -m pytest -q`.

## What it does

| Capability | Usage | Boundary |
|---|---|---|
| Task-aware skill search | `omniforge search "API errors"` | Local hybrid retrieval; optional neural embeddings require an already-installed model |
| Lazy skill load | `omniforge load log-triage` | Loads only one SKILL.md on request |
| VS Code MCP integration | `omniforge setup-vscode --project .` | Configures project-local `.vscode/mcp.json` |
| Local VS Code extension source | Open `vscode-extension/` and press F5 | Development Host only; not a published Marketplace extension |
| MCP bridge | `omniforge mcp` | Search, load, budget and read-only execution/browser previews |
| Skill installation | `omniforge install log-triage --agent codex --project .` | No overwrite without `--force` |
| Skill validation | `omniforge validate skills/my-skill` | Static format check |
| Skill audit | `omniforge audit skills/my-skill` | Heuristic check, not a malware scanner |
| CLI scaffold | `omniforge forge my-tool --description "..." --command tool` | Generates documentation only, never fetches or runs an unknown tool |
| Controlled script execution | `omniforge run --unsafe-local --approve firmware-preflight` | Docker isolation by default, approval required; host mode is **not sandboxed** |
| Multi-task coordination | `omniforge orchestrate workflow.json` | DAG execution with declared dependencies; no autonomous reasoning engine |
| Browser automation | `omniforge browser --url https://example.org --approve` | Requires optional Playwright and Chromium; actions limited to an approved host |
| BYOK code editing | `omniforge code --task "..." --file main.py --endpoint URL --model MODEL` | Sends only selected files, previews diff; `--apply` makes changes and keeps backups |
| SHA-256 manifest | `omniforge manifest --project .` | Local integrity check, **unsigned** |
| Blockchain provenance | `omniforge blockchain record --project .` | Local hash-chain + optional EVM anchor; wallet required for real transactions |
| Repo catalog | `omniforge catalog "firmware"` | 112 research candidates, not 112 integrated tools |

## Packaged skills (14)

**Built-in scripts:** `repo-recon`, `log-triage`, `dependency-inventory`, `sqlite-inspector`, `firmware-preflight`, `api-probe`, `python-symbols`, `git-diff-review`, `openapi-inventory`, `secret-hygiene`.

**Optional upstream tool adapters:** `trivy-scan`, `kicad-drc`, `esptool-chip`, `browser-snapshot`. Their check scripts work without downloading the upstream tools; actual integration depends on installation and system capabilities. Each adapter documents the upstream project. No upstream proprietary files or code are bundled.

## Controlled execution

Preview a bundled skill run (no process started):

```bash
omniforge run firmware-preflight
```

Run using Docker isolation, **after pulling the image yourself**:

```bash
docker pull python:3.13-alpine
omniforge run firmware-preflight --approve
```

Docker mode uses a read-only project mount, a read-only container filesystem, restricted memory/CPU/PIDs, dropped capabilities, no-new-privileges and `--network none` by default. It explicitly sets `--pull=never`; no image download is triggered by OmniForge. Isolation strength depends on a securely configured Docker host. On systems without Docker, `--unsafe-local` is an explicit opt-in; it is not a security sandbox.

For script-specific arguments, use `--` after the skill name; for example:

```bash
omniforge run --unsafe-local --approve python-symbols -- main.py
```

## Multi-task coordination

A workflow is a JSON file with one or more validated tasks. Dependencies run in order; independent tasks may run concurrently.

```json
{
  "tasks": [
    {"id":"hardware", "kind":"skill", "skill":"firmware-preflight"},
    {"id":"repository", "kind":"skill", "skill":"repo-recon", "depends_on":["hardware"]}
  ]
}
```

```bash
omniforge orchestrate workflow.json                # preview
omniforge orchestrate workflow.json --approve      # execute with Docker
omniforge orchestrate workflow.json --approve --unsafe-local  # host (not isolated)
```

External agent CLI tasks use `kind: "agent"`, an `executable` name and `args`. They require `--allow-command <name>` and `--approve`. OmniForge does not ship or authenticate external coding agents, and different provider CLI versions may require different arguments.

## Browser support

Install [Playwright](https://playwright.dev/python/docs/intro) and Chromium separately:

```bash
python -m pip install playwright
python -m playwright install chromium
```

The default command is preview-only; `--approve` initiates a session. Actions can be provided with `--actions actions.json` as a list containing `click`, `fill`, `wait`, `goto` and `screenshot` steps. Cross-domain navigation and private network hosts are blocked by default; use `--allow-local` deliberately for authorized local sites. This does not guarantee comprehensive protection against malicious websites.

## AI-assisted code edits

Requires an **explicit OpenAI-compatible endpoint** and provider-specific model name. Set `OMNIFORGE_API_KEY` in your environment when applicable. Do not send confidential files to third-party providers without authorization.

```bash
omniforge code --task "refactor the parser" --file parser.py \
  --endpoint https://YOUR-PROVIDER.example/v1/chat/completions \
  --model YOUR-MODEL --allow-remote
```

By default it previews the model's proposed unified diff. Add `--apply` only after reviewing it. The implementation enforces a user-selected file allowlist, checks original SHA-256 hashes, writes backups, and never runs model-generated shell commands. It is a single-pass assisted patch workflow, **not a fully autonomous coding agent**.

## MCP safety

The MCP server exposes `omniforge_search`, `omniforge_load`, `omniforge_budget`, `omniforge_run` and `omniforge_browser`. **The last two are preview-only.** No MCP request argument, environment flag, or model response can approve live execution. This prevents an AI agent from treating its own `approve: true` as human permission.

For an actual script run or browser session, invoke the **local CLI** yourself, inspect the target and arguments, and explicitly use `--approve`. Local CLI execution is a user operation; `--unsafe-local` bypasses Docker isolation and should be used only for trusted code. See [SECURITY.md](SECURITY.md).

## Search and token use

Default search is a local hybrid ranking of metadata. Use `--mode keyword` for the original exact-token router. Optional `--mode embeddings --model-path /path/to/local-model` requires the `sentence-transformers` package and an **already downloaded** embedding model. No model is downloaded automatically.

`omniforge budget --selected log-triage` estimates context size as characters divided by four; it is *not* a model tokenizer or billing meter. Lazy loading reduces unnecessary skill text compared with loading all skill documents, but end-to-end token savings depend on the host assistant.

## Test status and limitations

GitHub Actions runs the Python tests on Linux/Python 3.11–3.13. This release also provides an optional native extension source and modules for external tools, but does not claim their behavior has been verified on every supported machine. Windows/macOS CI, signed bundles, package-registry publication, fully autonomous iterative coding and 112 third-party integrations are **not** part of the verified core.

See [RELEASE_AUDIT.md](RELEASE_AUDIT.md), [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Blockchain provenance (v1.2.0)

**AI/MCP support:** `omniforge_chain_verify` and `omniforge_chain_proof` are read-only MCP tools. They never record entries or initiate wallet transactions.


OmniForge now includes a **local hash-chain ledger** for project/skill snapshot integrity and optional Ethereum-compatible transaction anchoring. The local ledger is **not a decentralized blockchain**; real on-chain anchoring requires a wallet and network gas. OmniForge never asks for your private key or sends transactions automatically.

```bash
omniforge blockchain record --project . --note "release build"
omniforge blockchain verify --project . --check-current
omniforge blockchain proof --project . --height 0

# Prepare unsigned self-transaction with ledger hash in calldata:
omniforge blockchain anchor --project . --wallet 0xYOUR_PUBLIC_ADDRESS --chain-id 1337

# After YOU sign/broadcast via wallet, verify using a trusted RPC:
omniforge blockchain verify-anchor --project . --wallet 0xYOUR_PUBLIC_ADDRESS --chain-id 1337 --rpc-url http://127.0.0.1:8545 --tx-hash 0xYOUR_TRANSACTION_HASH
```

The ledger lives at `.omniforge/chain.jsonl` and records SHA-256 snapshots without storing file contents. Local history can be rewritten by someone with filesystem access; anchoring an independently trusted head hash provides stronger evidence. A confirmed transaction is **not proof of authorship, licensing, or code safety**. See [Blockchain Guide](docs/BLOCKCHAIN.md).

## License

MIT for OmniForge code. Upstream software retains its own licenses and must be installed separately.

## Verified integration tests (v1.1.1)

GitHub Actions [real integration run](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100424908) passed four jobs on Linux:

- **Docker:** launched a real `python:3.13-alpine` container, read a private temporary project using the calling user's UID/GID, analyzed Python source, and completed a two-step dependency-ordered skill workflow. Project and skill script were mounted read-only, with networking disabled.
- **Playwright Chromium:** visited an authorized localhost test server, filled and clicked real page elements, and saved a screenshot in the project.
- **Model HTTP compatibility:** sent one explicitly chosen file to a local mock OpenAI-compatible server over real HTTP; verified the proposal, preview, approved apply, and backup restoration source.
- **VS Code:** packaged a VSIX and launched a real Linux VS Code Extension Development Host; verified command activation and the CLI diagnostics response.

Run the opt-in local integration tests only after installing their prerequisites:

```bash
python -m pip install -e . pytest playwright
python -m playwright install chromium
docker pull python:3.13-alpine
OMNIFORGE_LIVE=1 python -m pytest -q tests/test_live_integrations.py
```

The VS Code host test requires a graphical/Xvfb Linux runner and `@vscode/test-electron`; see `.github/workflows/e2e.yml`. Live browser, Docker and extension integration tests run automatically in that workflow when relevant source changes are pushed.

**Limits:** The integration suite uses a local test website and mock model server. It does *not* certify remote model providers, actual customer websites, Windows/macOS compatibility, or all threat models.
