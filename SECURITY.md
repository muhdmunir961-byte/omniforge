# Security policy

OmniForge executes commands only after explicit user approval. Its default MCP skills execution is **disabled** unless the host process sets `OMNIFORGE_MCP_EXECUTION=1`. Browser execution is separately disabled unless the host sets `OMNIFORGE_MCP_BROWSER=1`. Agent tools can sometimes set request-level arguments autonomously, so never enable these flags for an agent you do not trust.

Docker isolation mounts the project and script read-only, drops capabilities, disables network by default and has resource caps. It is **not** a complete solution against kernel exploits, Docker daemon compromise or device-level side effects. Docker images must be pulled by the operator, and OmniForge sets `--pull=never`. `--unsafe-local` deliberately bypasses isolation.

Do not run third-party scripts merely because `omniforge audit` reports no findings. Its static scan is heuristic and can miss attacks or flag benign content. Review supporting scripts and dependencies before installation.

Browser automation should only target sites you control or are authorized to test. The browser policy blocks private/IP and cross-domain targets at the application layer by default, but does **not** provide perfect SSRF or DNS rebinding protection.

For `omniforge code`, only user-specified files are sent to the provided model endpoint; never select a file containing credentials or personal data unless disclosure is authorized. The resulting patch is restricted to selected files, protects against concurrent edits with SHA-256, and uses local backups. This does not make generated code inherently safe: review the diff and test it.

Do not send secrets, tokens or credentials in bug reports. Report security-sensitive issues privately using GitHub Security Advisories.
