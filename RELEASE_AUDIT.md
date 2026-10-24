# OmniForge v1.0 — release audit

Date: 2026-10-24

## Verified locally

- Python source test suite: **23 passed** on Python 3.13.
- `pip install -e . --no-build-isolation --no-deps`: succeeded with locally installed setuptools.
- Built a distributable Python wheel using `pip wheel --no-build-isolation --no-deps`.
- Installed wheel into an isolated target and verified 10 skills, 112 candidate records and MCP tools/list.
- Tested JSON-RPC initialize, notification suppression, tools/list, search and lazy document loading.
- Tested all 10 skill scripts using realistic temporary project data or an authorized localhost HTTP listener.
- VS Code MCP configuration merging was tested; existing user entries are preserved.

## Known limitations

1. This is a **local v1.0 code release**. GitHub release tag, PyPI distribution and VS Code marketplace extension are **not** published.
2. MCP only exposes skill discovery, document loading and rough budget calculation; it cannot execute arbitrary tools or autonomously code and deploy a project.
3. The 112 third-party projects are **discovery candidates, not 112 verified integrations**.
4. Keyword-based router has no semantic embeddings. Matching other languages may be weaker than English.
5. The token estimate is approximate (`ceil(characters / 4)`) and omits host-specific context overhead.
6. Static heuristic audits can miss malicious code and flag benign regex rules. In this release `log-triage` and `secret-hygiene` each trigger a known heuristic `credential-reference` false positive in their own redaction/scanning regex. These were inspected manually but are **not proof of full safety**.
7. Python 3.11+ only. CI is configured for 3.11–3.13 on GitHub-hosted Linux; Windows/macOS compatibility is not yet verified.
8. No claims of outperforming Codex, Claude Code or other proprietary agents are supported by comparative benchmarks.

## Practical release status

**Core functional locally; packaging verified; external publication pending.**
