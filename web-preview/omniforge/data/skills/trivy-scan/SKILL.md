---
name: trivy-scan
description: "Scan a local project for vulnerabilities or secrets using installed Trivy; requires opt-in for database downloads."
---
# trivy-scan

Optional upstream dependency: https://github.com/aquasecurity/trivy

Use this skill when the task explicitly requires it. Preview arguments before executing; inspect output and avoid sending secrets to external services.

- Availability check: `python scripts/check.py --check`
- Usage: `trivy fs --scanners vuln,secret --format json`
- Actual external tool execution requires the upstream binary (or Playwright) to be installed separately.
- No upstream code is bundled or copied into OmniForge.
- Obtain approval before network requests, serial communication, browser interaction or modifying files.
