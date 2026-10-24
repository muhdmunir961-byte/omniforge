<div align="center">

# OMNIFORGE

### An open capability layer for AI coding agents.

**Find the right skill. Load it only when needed. Inspect before installing.**

![Version](https://img.shields.io/badge/release-v1.0.0-252525) ![Python](https://img.shields.io/badge/python-3.11%2B-3776ab) ![License](https://img.shields.io/badge/license-MIT-202a23) ![MCP](https://img.shields.io/badge/MCP-stdio-202a23)

[Quickstart](#quickstart) · [CLI](#cli-commands) · [VS Code](#vs-code-integration) · [Security](SECURITY.md) · [Scope](ROADMAP.md)

</div>

## Why OmniForge?

Modern coding agents can use external tools, but a large collection of instructions can overwhelm context. OmniForge makes agent skills **discoverable and available on demand**. An MCP client can search compact metadata and request exactly one `SKILL.md` when needed.

OmniForge does **not** provide a replacement language model, a fully autonomous coding agent, or an empirical claim of outperforming Codex or Claude Code. It is a **vendor-neutral local skill layer** that works alongside AI coding assistants.

### What is implemented in v1.0.0?

| Component | Status | What it does |
|---|---|---|
| CLI | ✅ Implemented + tested | `omniforge` / `oforge` terminal commands |
| Skills directory | ✅ Implemented + tested | 10 bundled, script-backed Agent Skill packages |
| Lazy skill router | ✅ Implemented + tested | Metadata lookup; full instructions loaded only on request |
| MCP stdio bridge | ✅ Implemented + tested | Search, load, and budget tools over JSON-RPC |
| VS Code setup | ✅ Implemented + tested | Writes `.vscode/mcp.json` and short optional instructions |
| Agent installers | ✅ Implemented + tested | Codex, Claude, Cursor, OpenCode, Copilot, Gemini |
| Local repo inspection | ✅ Implemented + tested | Detects project language/tooling without running files |
| Static safety audit | ✅ Heuristic only | Metadata validation and suspicious-text detection |
| Tool discovery catalog | ✅ Bundled | 112 **unverified candidate** GitHub tools (not implementations) |
| Multi-agent autonomous orchestration | ❌ Not in v1.0 | Separate, future runtime effort |
| Browser and terminal remote execution | ❌ Not in v1.0 | Not safe or implemented as a default capability |

## Quickstart

Requirements: **Python 3.11+**. The core has no third-party runtime dependencies.

```bash
git clone https://github.com/muhdmunir961-byte/omniforge.git
cd omniforge
python -m pip install -e .

omniforge doctor
omniforge search "sqlite database schema"
omniforge load sqlite-inspector
omniforge budget --selected sqlite-inspector
```

Maintained at https://github.com/muhdmunir961-byte/omniforge.

Without installing (inside the checked-out project):

```bash
PYTHONPATH=src python -m omniforge doctor
PYTHONPATH=src python -m omniforge search "network api"
```

On Windows PowerShell, set `$env:PYTHONPATH = 'src'` before `python -m omniforge ...`.

## VS Code integration

Install OmniForge into the same environment your VS Code terminal uses, then from the **target project**, run:

```bash
omniforge setup-vscode --project .
```

The generated `.vscode/mcp.json` exposes a server with three read-only MCP tools:

- `omniforge_search` — compact capability discovery.
- `omniforge_load` — expand one selected skill document.
- `omniforge_budget` — estimate context cost of loading strategies.

The optional `.github/instructions/omniforge.instructions.md` does **not** use global `applyTo`; attach it manually if desired. You can instead install selected skills into the agent's normal skill directory, so the client discovers them using its native Agent Skills support.

```bash
omniforge install log-triage --agent codex --project .
omniforge install sqlite-inspector --agent claude --project .
omniforge install firmware-preflight --agent copilot --project .
```

Never install all 112 catalog candidates: they are research leads, not packaged or vetted skills.

## Token-friendly by design

Agent Skills use [progressive disclosure](https://agentskills.io/specification): metadata first, full instructions on task match, related scripts when required. OmniForge follows that model. **Important:** agents may already implement progressive disclosure; OmniForge isn't claiming to have invented this approach.

Try:

```bash
omniforge budget --selected log-triage
```

Example from a local test build (10 bundled skills): metadata **~334 tokens**, all skill documents **~2,293 tokens**, metadata plus selected `log-triage` **~600 tokens**. Numbers use a crude `characters / 4` heuristic, not actual API billing, and exclude client-specific prompt overhead.

If you're vibe coding in VS Code, **do not paste dozens of SKILL.md files into every prompt**. Keep only routing metadata available and load relevant instructions when required. This saves context versus a naïve all-at-once prompt, but does not guarantee lower overall token usage on every coding task.

## Bundled operational skills

| Skill | Script purpose | Side effect / boundary |
|---|---|---|
| `repo-recon` | Read Git metadata, tracked file counts | Local, read-only |
| `log-triage` | Group common log errors with redaction | Local, read-only |
| `dependency-inventory` | Inspect local dependency declarations | Local, read-only |
| `sqlite-inspector` | Read SQLite schema and optional counts | Local database opens in read-only mode |
| `firmware-preflight` | Check ESP32-related tooling/serial ports | Device enumeration only |
| `api-probe` | Probe authorized HTTP(S) endpoint headers | **Network request**; review target first |
| `python-symbols` | Parse Python AST without running source | Local, read-only |
| `git-diff-review` | Summarize Git diff stats, not contents | Local, read-only |
| `openapi-inventory` | Summarize OpenAPI JSON paths and methods | Local, read-only |
| `secret-hygiene` | Identify probable secret leaks without printing values | Local, heuristic, read-only |

**Note:** Bundled scripts are tools invoked separately by the user or host coding agent, as documented in each skill. The MCP bridge intentionally does not execute scripts.

## CLI commands

```text
omniforge doctor
omniforge list
omniforge search "my task" --limit 5
omniforge load log-triage
omniforge budget --selected log-triage
omniforge catalog "network" --category network
omniforge inspect /my/project
omniforge validate path/to/skill
omniforge audit path/to/skill
omniforge install log-triage --agent codex --project .
omniforge forge my-cli --description "Analyze Foo CLI outputs" --command foo
omniforge setup-vscode --project .
omniforge mcp
```

### Creating a skill

```bash
omniforge forge local-diagnostics \
  --description "Help debug an authorized local service" \
  --command my-cli \
  --output ./skills
omniforge audit ./skills/local-diagnostics
```

Forge produces a **documentation scaffold**, never automatically executes or downloads unknown code. Review the generated instructions and add real tests before sharing.

### External skill installation

```bash
omniforge audit ./skills/my-reviewed-skill
omniforge install my-reviewed-skill --source ./skills/my-reviewed-skill --agent codex --project .
```

Auditing is **heuristic**, not a security guarantee. Trust the source and inspect all supporting scripts before use. `--force` can replace an existing skill directory; use with care.

## Architecture

```text
VS Code / Codex / Claude / Cursor / OpenCode / Gemini
       |                         |
       | native skill folder     | MCP stdio
       v                         v
    Installed SKILL.md       OmniForge MCP tools
                                   |
                           Metadata-only router
                                   |
                  +----------------+-----------------+
                  |                                  |
             Load one skill                   Candidate catalog
                  |                                  |
        Local script instructions              112 discovery leads
                  |
           User/agent invokes script
           (outside MCP server)
```

No background telemetry, model provider login, API tokens, or network access are required for OmniForge core operation. The `api-probe` script explicitly makes a network request when the user runs it.

## Development

```bash
python -m pip install -e .
python -m pip install pytest
python -m pytest -q
```

Offline source tests when pytest is already present:

```bash
PYTHONPATH=src python -m pytest -q
```

## Contributing

We welcome integration tests, new local-first skills, docs, accessibility and platform compatibility fixes. Every skill PR should clearly state its permissions, inputs, dependencies, upstream repo and license. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

MIT for OmniForge source, plus respect each referenced upstream project's separate license. Candidate upstream software is **not vendored** in this distribution.
