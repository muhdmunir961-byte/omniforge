# Security policy

OmniForge's **MCP interface is preview-only for execution and browser tools**, regardless of request parameters or environment variables. A model-supplied `approve: true` never authorizes a shell command or browser session. Use the local CLI with an explicit `--approve` flag for actions you have reviewed. CLI approval is a user opt-in, not proof of an independent permission broker.

Skill installation, VS Code configuration, AI patch backups, and screenshots reject symlinked destination paths beneath the project; this mitigates symlink-based escapes but does **not** prevent time-of-check/time-of-use (TOCTOU) races against a concurrently malicious filesystem process. Do not run tools against hostile worktrees or allow untrusted processes to alter the project simultaneously.

Docker isolation mounts the project and script read-only, drops capabilities, runs under the caller's Linux UID/GID (instead of root where available), disables network by default and has resource caps. It is **not** a complete solution against kernel exploits, Docker daemon compromise or device-level side effects. Docker images must be pulled by the operator, and OmniForge sets `--pull=never`. `--unsafe-local` deliberately bypasses isolation.

Do not run third-party scripts merely because `omniforge audit` reports no findings. Its static scan is heuristic and can miss attacks or flag benign content. Review supporting scripts and dependencies before installation.

Browser automation should only target sites you control or are authorized to test. The browser policy blocks private/IP and cross-domain targets at the application layer by default, but does **not** provide perfect SSRF or DNS rebinding protection.

For `omniforge code`, only user-specified files are sent to the provided model endpoint; never select a file containing credentials or personal data unless disclosure is authorized. The resulting patch is restricted to selected files, protects against concurrent edits with SHA-256, and uses local backups. This does not make generated code inherently safe: review the diff and test it.

Do not send secrets, tokens or credentials in bug reports. Report security-sensitive issues privately using GitHub Security Advisories.

## Blockchain provenance v1.2.0

The local `.omniforge/chain.jsonl` ledger can be rewritten by an attacker with filesystem write access. Hash links alone do not provide decentralized consensus, digital signatures, copyright ownership or a software safety certification. Keep a trusted copy of the head hash or anchor it independently if tamper-evidence matters.

On-chain anchoring produces only an unsigned **zero-value self-transaction** with a 32-byte digest in EVM calldata. The user must approve gas and broadcast with their own wallet. OmniForge never requests private keys or recovery phrases or transmits a transaction.

Remote JSON-RPC calls must use HTTPS (local loopback HTTP is allowed). The verifier relies on the RPC provider, cannot prove an independent consensus history and cannot guarantee finality against reorganizations. Addresses and calldata on public networks are visible forever. Never place secrets in ledger notes or RPC URLs.

## OF-Provenance v2 security boundaries (OmniForge 1.3.0)

- A fully writable local ledger can be rewritten, including recomputed hashes. Full rewrite/rollback detection requires a trusted external **sequence and head hash**; never derive trusted checkpoints from the suspect ledger.
- v2 records contain immutable historical scan policy and explicit exclusions, including .env. Excluded source files are outside the covered scope. Duplicate JSON keys, unsupported fields, unsafe paths and incorrect links are rejected.
- Local anchor receipt journal entries are not independent on-chain proof. RPC providers may lie or become stale due to reorganization. Check live RPC again for important decisions.
- Migration is preview-first, copy-only with approval; old v1 hash/anchors are retained without conversion.
- EVM preparation requires explicit public-data acknowledgement; OmniForge NEVER stores private keys, signs, broadcasts or pays gas. The user's separate wallet controls any transaction.
- Export backup to a new directory OUTSIDE the project and preserve checkpoint copies under independently controlled storage. Same-host mutable backups are not independent trusted checkpoints.
- POSIX openat and locking mitigate common races; hostile concurrent filesystem changes and non-POSIX systems are not formally certified.

Required warnings: Ledger setempat boleh diubah oleh sesiapa yang ada akses fail. Anchoring ke EVM tidak membuktikan pemilikan atau keselamatan kod. Jangan masukkan rahsia dalam nota anchor. Data on-chain kekal kelihatan selama-lamanya.
