---
name: openapi-inventory
description: "Summarize endpoints, request methods, and response codes in an existing local OpenAPI JSON file without network calls."
---

# openapi-inventory

## When to use
Use this skill for: summarize endpoints, request methods, and response codes in an existing local openapi json file without network calls.

## Requirements
Python 3.11+ (standard library only).

## Run

```bash
python scripts/openapi_inventory.py --help
```

Provide an explicit, authorized local path as required by the script.
Do not run untrusted repositories' code; this script only reads source data.
Inspect results and confirm findings manually before taking action.
