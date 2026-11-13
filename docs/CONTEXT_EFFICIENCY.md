# Low-context mode (no large content cache)

## Goals
- Reduce repeated source and skill bodies in AI conversation context.
- Avoid unnecessary questions whose answers are already in the task or repo.
- Bound individual read responses. Do not introduce persistent content caches.

## Source reads (local CLI only)
```bash
omniforge context src/omniforge/router.py --project . --start-line 1 --max-lines 70
omniforge context src/omniforge/router.py --project . --known-sha256 <DIGEST>
```
The first request returns a line-numbered excerpt and the SHA-256 of the full
file. The second returns `status: unchanged` and an empty body if that digest
still matches. Pass the digest between calls using the agent's existing
conversation state, not a new database. Defaults: 100 lines, 6,000 characters;
hard limits: 160 lines, 12,000 characters, 256 KB files.

The tool reads one explicitly requested file, does not recurse, and rejects
hidden paths, typical generated/credential paths, symlinks, and unknown source
extensions. It is **not** an authorization boundary for file contents; secrets
may still exist in allowed source files. Inspect the path before sharing text.

## Skill reads (CLI and MCP)
```bash
omniforge load log-triage
omniforge load log-triage --known-sha256 <DIGEST>
```
MCP `omniforge_load` accepts the optional `known_sha256` parameter. Omit it
for first use or when deliberately refreshing. An unchanged digest produces
empty `content` but preserves metadata and a status string.

## Token accounting
`omniforge budget` uses file sizes rather than reading every skill body.
Token counts remain heuristics, **not** accurate provider billing data. Actual
provider input, output, cache-read and cache-write tokens should be obtained
from model response usage metadata. Disabling beneficial provider prompt
caching can increase cost: optimize **repeated payloads**, not cache-hit rates
in isolation.

## What this does not do
- Does not intercept file reads by Claude Code, Codex or other independent tools.
- Does not keep a persistent cache of file contents.
- Does not guarantee a user-facing agent will ask zero redundant questions.
- Does not eliminate local file I/O when checking SHA-256 freshness.

For behavioral guidance, see `AGENTS.md` in the repository root.
