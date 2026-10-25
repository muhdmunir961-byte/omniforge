---
name: git-diff-review
description: "Review local Git diff statistics and changed files without modifying the repository or showing secret contents."
---

# git-diff-review

## When to use
Use this skill for: review local git diff statistics and changed files without modifying the repository or showing secret contents.

## Requirements
Python 3.11+ (standard library only).

## Run

```bash
python scripts/git_diff_review.py --help
```

Provide an explicit, authorized local path as required by the script.
Do not run untrusted repositories' code; this script only reads source data.
Inspect results and confirm findings manually before taking action.
