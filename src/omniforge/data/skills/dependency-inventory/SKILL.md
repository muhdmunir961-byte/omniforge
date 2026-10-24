---
name: dependency-inventory
description: "Inventory declared Python and Node.js dependencies in a local project without installing or executing packages."
---

# dependency-inventory

Use this skill when the user needs: inventory declared Python and Node.js dependencies in a local project without installing or executing packages.

## Workflow

1. Confirm the project path, file or target belongs to the user or is authorized.
2. Review `scripts/dependency_inventory.py` before first use; it is bundled Python standard-library code.
3. Run `python scripts/dependency_inventory.py --help` from this skill directory to see supported arguments.
4. Run with the minimum required permissions and pass an explicit target path or URL.
5. Interpret the JSON output, check limitations, and report only observed results.
6. Ask before any changes, package installs, or privileged operations (this script does not require them).

## Limitations

This is a targeted operational helper, not a general-purpose agent or a security guarantee.
For network probes, use only endpoints that the user authorizes.
