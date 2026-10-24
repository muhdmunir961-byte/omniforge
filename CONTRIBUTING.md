# Contributing to OmniForge

Issues, documentation fixes, portability patches and verified skill packages are welcome.

1. Open an issue describing a real-world use case with upstream license and documentation.
2. Add a skill under `src/omniforge/data/skills/<kebab-case>/SKILL.md` and its minimal working script where appropriate.
3. Use the Agent Skills `name` and `description` metadata, keeping the instructions short and accurate.
4. Add examples (`--help` and a read-only workflow), platform requirements, and tests in `tests/`.
5. Run `PYTHONPATH=src python -m pytest -q` before proposing a PR.
6. Disclose whether your skill makes network requests, writes files, elevates privileges or touches secrets.
7. Include evidence for any advertised benchmark improvements.

Catalog candidates must not be labeled production-ready until integrated and tested.

We welcome honest community sharing but not GitHub-star manipulation, spam or misleading feature claims.
