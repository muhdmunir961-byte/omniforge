---
name: kicad-drc
description: "Check PCB design-rule violations using the installed KiCad kicad-cli command."
---
# kicad-drc

Optional upstream dependency: https://gitlab.com/kicad/code/kicad

Use this skill when the task explicitly requires it. Preview arguments before executing; inspect output and avoid sending secrets to external services.

- Availability check: `python scripts/check.py --check`
- Usage: `kicad-cli pcb drc`
- Actual external tool execution requires the upstream binary (or Playwright) to be installed separately.
- No upstream code is bundled or copied into OmniForge.
- Obtain approval before network requests, serial communication, browser interaction or modifying files.
