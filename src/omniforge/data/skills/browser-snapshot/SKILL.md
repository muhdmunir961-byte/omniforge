---
name: browser-snapshot
description: "Capture a browser snapshot or interact with approved pages using optional local Playwright."
---
# browser-snapshot

Optional upstream dependency: https://github.com/microsoft/playwright-python

Use this skill when the task explicitly requires it. Preview arguments before executing; inspect output and avoid sending secrets to external services.

- Availability check: `python scripts/check.py --check`
- Usage: `python -m omniforge browser`
- Actual external tool execution requires the upstream binary (or Playwright) to be installed separately.
- No upstream code is bundled or copied into OmniForge.
- Obtain approval before network requests, serial communication, browser interaction or modifying files.
