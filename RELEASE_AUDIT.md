# OmniForge 1.3.0 / OF-Provenance v2 — Remediation Audit

Audit date: 2026-10-25

## Status and evidence

- Strict OF-Provenance v2 is implemented as a separate command namespace (`ofprov`, `omniforge provenance`) while legacy v1 `omniforge blockchain` remains available. v1 hash values and original files are not rewritten.
- Linux/Python 3.11, 3.12 and 3.13 regression runs: **112 passed, 6 skipped per version** as observed in successful GitHub Actions [CI run 40131000600](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40131000600). Skipped tests are opt-in E2E, and are evaluated separately.
- [Real Integrations E2E run 40130983003](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40130983003): **all five jobs passed**, covering real Foundry Anvil local-chain anchoring of v1/v2, native VS Code host, VSIX packaging, Chromium interaction, local model HTTP, and isolated Docker execution.
- Foundry Anvil installed through official maintained `foundry-rs/foundry-toolchain@v1` with binary version `v1.8.6`; the tests explicitly wait for a mined transaction receipt rather than assuming immediate finality.

## Resolved audit findings

1. **Strict schema verification:** no extra fields, duplicate JSON keys, non-canonical relative paths, malformed project UUIDs, invalid UTC values, Boolean masquerading as int, or wrong link/snapshot/policy hashes.
2. **Immutable complete policy history:** full scan policy and policy hash stored in each snapshot, policy changes require explicit `--allow-policy-change`.
3. **External trusted checkpoints:** verification of independently stored `expected_seq` and `expected_head` can detect entire rewritten/truncated local history; absent an external trust anchor, local ledger is not tamper-proof.
4. **Copy-only migration:** existing v1 ledger and optional anchor metadata archived byte-for-byte and linked from new v2 genesis. Legacy v1 current-source checks still work following migration.
5. **Resource and filesystem controls:** file count/size/total scan limits, 10 MB/10,000-entry ledger caps, symlink/nonregular rejection, POSIX nofollow descriptor opens, change-during-hash detection, fsync and writer locks.
6. **Anchor metadata isolation:** immutable v2 chain maintains `anchor_status: not_requested`; optional receipt events stored in a hash-linked local journal, explicitly **untrusted** until rechecked against a live RPC.
7. **External backup and manual recovery:** backup and SHA-256 manifest/checkpoint export to a new external directory; manual restore verified by regression test, without silently altering old history.
8. **Privacy and EVM consent:** public-data acknowledgement is required for unsigned anchor preparation; applications never accept private keys or sign/broadcast transactions; actual wallet operation is separate.
9. **Docs and tests:** full [Malay design and CLI guide](docs/PROVENANCE_V2.ms.md), [strict JSON schema](docs/PROVENANCE_V2_SCHEMA.json), expanded positive/negative/concurrent tests, and full EVM integration.

## Remaining limitations, not a security certification

- The local hash chain is rewritable by an attacker controlling all local files. A same-host checkpoint is not independent; use externally trusted versioned/offline storage.
- A provider's JSON-RPC response and local receipt journal do not independently establish blockchain consensus or ownership. Chain reorganizations and dishonest providers remain possible.
- Test transactions run on disposable **local Anvil** with simulated balances, not public mainnet/testnet wallet funds.
- Windows/macOS concurrent malicious filesystem races and external penetration tests remain unverified.
- Source hashes do not prove malware-free code, copyright, identity or full project integrity for intentionally excluded files.

---

# OmniForge 1.2.0 — Blockchain Provenance Audit

Date: 2026-10-24

## Scope verified

- SHA-256 local provenance chain with timestamp, previous record hash and project snapshot hash.
- Validation of chain structure, tamper/truncation detection, current source snapshot checks, symlink rejection and concurrent writers.
- CLI record/verify/proof/anchor/verify-anchor, with unsigned EVM self-transaction payloads (no wallet keys).
- Read-only RPC verification of network chain ID, sender/recipient, exact calldata, transaction receipt success and confirmations.
- Real in-memory Ganache EVM network (chain ID 1337), with a 0-value on-chain transaction and successful RPC verification.
- Negative test: a different ledger height must not validate against the earlier transaction.
- GitHub EVM CI evidence: https://github.com/muhdmunir961-byte/omniforge/actions/runs/40105634750
- Extended reference: docs/BLOCKCHAIN.md

## Limitations and security boundaries

- This is an application-level local hash chain plus optional anchor to an external EVM-compatible blockchain, NOT a newly implemented consensus network, wallet, cryptocurrency or token.
- An attacker with local write access can recompute the entire chain. An independently saved or anchored hash is necessary to meaningfully detect a complete rewrite.
- OmniForge never signs or broadcasts transactions. Users are responsible for the wallet, gas fee, network choice, confirmation depth and any financial or privacy implications.
- Public-chain anchoring has not been tested on a real testnet or mainnet; CI confirms behavior against a disposable local Ganache node.
- JSON-RPC verifier trusts the chosen provider's responses; it does not validate PoS consensus or guarantee finality.
- SHA-256 identifies file snapshots, not authorship, source licensing or absence of malicious code.
- This change has not been independently penetration-tested. Windows/macOS filesystem locking is not yet validated.

---

# OmniForge 1.1.1 — previous audit

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

- A real Playwright Chromium session against a controlled localhost site was tested in GitHub Actions; third-party websites and authentication flows are not exhaustively validated.
- A real Docker sandbox was tested with `python:3.13-alpine`, read-only mounts, blocked networking, and owner UID/GID on Linux. This is functional integration evidence, not a formal sandbox security audit.
- Neural embedding retrieval requires the optional package and an already installed local model; offline fallback is hybrid text ranking.
- Actual external Trivy/KiCad/esptool commands require their respective executables and hardware/files.
- Model HTTP request/response, preview/apply and backup behavior were tested using a real HTTP connection to a controlled local OpenAI-compatible mock server. External providers and model quality remain unverified.
- VSIX packaging and VS Code Extension Development Host command activation/CLI output were tested on Linux; Marketplace publication and Windows/macOS editor compatibility remain unverified.
- Agent task coordinator is deterministic workflow execution, not autonomous iterative goal planning.
- SHA-256 inventory is **unsigned** and does not authenticate a maintainer identity.
- Existing upstream catalog of 112 tools is still candidate-only.

## Published source verification

- Python package version: **1.1.1**, published as source code on the repository default branch.
- Hardened upgrade published successfully by GitHub Actions run [40088583617](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40088583617).
- Post-publication CI run [40088762489](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40088762489): **64/64 tests passed** independently on Linux/Python 3.11, 3.12 and 3.13; native VS Code extension Node smoke passed.
- MCP tool requests cannot grant human approval; actual actions require an independently invoked local CLI `--approve` flag.
- Destination symlink checks mitigate accidental escapes, but do not prevent concurrent path-swap/TOCTOU attacks. Do not run on hostile worktrees while another process can mutate paths.
- These automated tests do not establish live Playwright compatibility, real Docker isolation, external API availability, full security certification or package registry publication.

## End-to-end verification, 24 October 2026

- Verified GitHub Actions run: [40100424908](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100424908).
- All four jobs passed: `docker-sandbox`, `browser-model`, `vscode-package`, `vscode-host`.
- The Docker private-directory read failure (`PermissionError: /workspace/sample.py`) was reproduced, fixed by using owner UID/GID in the container, then verified using real Docker execution.
- Browser interaction used a local HTTP page, Playwright Chromium, form entry, click and PNG screenshot.
- The model integration used a local OpenAI-compatible HTTP server, confirmed selected-file-only transmission, preview and approved source editing with backup.
- The VS Code integration launched an actual extension host, registered commands and displayed parsed CLI diagnostics; the VSIX package was built successfully.
- Linux only for these integrations; external models, hostile websites, Windows/macOS and formal penetration testing remain outside verified scope.
