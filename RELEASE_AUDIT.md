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
- Disabled-by-default MCP tool execution and browser navigation.
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

Python package version: 1.1.0. GitHub CI results for this upgrade should be recorded only after a successful workflow run. Do not reuse v1.0 CI evidence as proof of the new features.
