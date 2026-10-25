---
name: esptool-chip
description: "Read chip identification from an explicitly selected ESP32 serial port using installed esptool."
---
# esptool-chip

Optional upstream dependency: https://github.com/espressif/esptool

Use this skill when the task explicitly requires it. Preview arguments before executing; inspect output and avoid sending secrets to external services.

- Availability check: `python scripts/check.py --check`
- Usage: `esptool --port PORT chip-id`
- Actual external tool execution requires the upstream binary (or Playwright) to be installed separately.
- No upstream code is bundled or copied into OmniForge.
- Obtain approval before network requests, serial communication, browser interaction or modifying files.
