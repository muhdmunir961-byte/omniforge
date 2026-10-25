---
name: secret-hygiene
description: "Flag likely credentials in local source trees and report only file names, line numbers, and pattern types without exposing values."
---

# secret-hygiene

## When to use
Use this skill for: flag likely credentials in local source trees and report only file names, line numbers, and pattern types without exposing values.

## Requirements
Python 3.11+ (standard library only).

## Run

```bash
python scripts/secret_hygiene.py --help
```

Provide an explicit, authorized local path as required by the script.
Do not run untrusted repositories' code; this script only reads source data.
Inspect results and confirm findings manually before taking action.
