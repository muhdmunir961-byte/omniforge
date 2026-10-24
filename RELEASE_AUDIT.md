# OmniForge 1.1.0 audit

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

- Browser end-to-end interaction requires a Playwright Chromium installation and an authorized live website; these are not covered by the offline unit suite.
- Docker operation requires a suitable container daemon and locally pulled image; the offline suite validates command construction and policy, not actual container isolation.
- Neural embedding retrieval requires the optional package and an already installed local model; offline fallback is hybrid text ranking.
- Actual external Trivy/KiCad/esptool commands require their respective executables and hardware/files.
- BYOK model calls depend on a compatible remote or local provider. The suite checks local validation and atomic application, not live model quality.
- Native VS Code extension is development source; JavaScript syntax can be checked, but Marketplace packaging, UI host behavior and platform portability require further validation.
- Agent task coordinator is deterministic workflow execution, not autonomous iterative goal planning.
- SHA-256 inventory is **unsigned** and does not authenticate a maintainer identity.
- Existing upstream catalog of 112 tools is still candidate-only.

## Published source verification

- Python package version: **1.1.0**, published as source code on the repository default branch.
- Hardened upgrade published successfully by GitHub Actions run [40088583617](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40088583617).
- Post-publication CI run [40088762489](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40088762489): **64/64 tests passed** independently on Linux/Python 3.11, 3.12 and 3.13; native VS Code extension Node smoke passed.
- MCP tool requests cannot grant human approval; actual actions require an independently invoked local CLI `--approve` flag.
- Destination symlink checks mitigate accidental escapes, but do not prevent concurrent path-swap/TOCTOU attacks. Do not run on hostile worktrees while another process can mutate paths.
- These automated tests do not establish live Playwright compatibility, real Docker isolation, external API availability, full security certification or package registry publication.
