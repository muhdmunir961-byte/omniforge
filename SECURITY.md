# Security Policy

## Supported releases

Security fixes target the current supported OmniForge release. Prefer GitHub private vulnerability reporting when it is enabled on the repository.

## Threat model and limitations

Skills can contain instructions that lead agents into destructive commands, leaked credentials or unsafe network actions. **Never execute unreviewed remote code.** `omniforge audit` checks only selected text patterns and structural rules. It does **not** sandbox code, detect all prompt injections, verify dependencies or guarantee safety.

OmniForge's MCP server is *discovery-only* and cannot run arbitrary shell commands. It exposes only read-only search, load and budget tools. Bundled skill scripts are invoked outside the MCP server by the user or their coding agent. Some scripts (especially `api-probe`) may make explicit network requests when invoked. Do not use them against unauthorized targets.

Installing a skill copies local instructions and scripts into the target agent's skill directory. The user and the host agent are responsible for reviewing those scripts. Avoid `--force` unless you have backed up the destination.

## Safe defaults

- Never embed credentials or `.env` in skills and repositories.
- Review PRs, pin dependencies and inspect upstream licensing before adding third-party tools.
- Use least-privilege credentials and test untrusted content in disposable environments.
- Require explicit human approval for filesystem writes, package installation, secret handling and remote deployment.
- Do not assume an instruction file is trustworthy merely because it is syntactically valid.
