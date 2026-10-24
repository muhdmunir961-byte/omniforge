---
name: sqlite-inspector
description: "Inspect SQLite schemas and table row-count estimates using read-only queries without altering local databases."
---

# sqlite-inspector

Use this skill when the user needs: inspect SQLite schemas and table row-count estimates using read-only queries without altering local databases.

## Workflow

1. Confirm the project path, file or target belongs to the user or is authorized.
2. Review `scripts/sqlite_inspector.py` before first use; it is bundled Python standard-library code.
3. Run `python scripts/sqlite_inspector.py --help` from this skill directory to see supported arguments.
4. Run with the minimum required permissions and pass an explicit target path or URL.
5. Interpret the JSON output, check limitations, and report only observed results.
6. Ask before any changes, package installs, or privileged operations (this script does not require them).

## Limitations

This is a targeted operational helper, not a general-purpose agent or a security guarantee.
For network probes, use only endpoints that the user authorizes.
