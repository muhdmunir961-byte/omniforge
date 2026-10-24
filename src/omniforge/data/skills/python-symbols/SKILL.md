---
name: python-symbols
description: "Inspect Python source file classes, functions, imports, and asynchronous definitions using safe AST parsing."
---

# python-symbols

## When to use
Use this skill for: inspect python source file classes, functions, imports, and asynchronous definitions using safe ast parsing.

## Requirements
Python 3.11+ (standard library only).

## Run

```bash
python scripts/python_symbols.py --help
```

Provide an explicit, authorized local path as required by the script.
Do not run untrusted repositories' code; this script only reads source data.
Inspect results and confirm findings manually before taking action.
