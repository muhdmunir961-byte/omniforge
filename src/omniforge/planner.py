"""Offline task planning and lexical-semantic retrieval for OmniForge.

No external model, network calls or command execution.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from .router import index

ALIASES = {
    "error": ("failure", "exception", "crash", "bug", "traceback", "debug"),
    "api": ("endpoint", "http", "request", "rest", "network"),
    "database": ("sql", "sqlite", "schema", "table", "db"),
    "firmware": ("esp32", "arduino", "microcontroller", "serial", "hardware"),
    "security": ("secret", "credential", "token", "password", "key"),
    "dependency": ("package", "library", "requirements", "lockfile"),
    "repository": ("repo", "git", "project", "codebase"),
}
def _terms(value: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9][a-z0-9_-]+", value.lower()))
    expanded = set(words)
    for canonical, variants in ALIASES.items():
        family = {canonical, *variants}
        if words & family:
            expanded.update(family)
    return expanded

def related(query: str, limit: int = 5) -> list[dict]:
    """Weighted token similarity with synonym expansion; not neural embeddings."""
    if not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    q = _terms(query)
    if not q:
        return []
    docs = index()
    vocab = [_terms(x["name"].replace("-", " ") + " " + x["description"]) for x in docs]
    counts = Counter(t for doc in vocab for t in doc)
    def weight(t: str) -> float:
        return math.log((len(vocab) + 1) / (counts[t] + 1)) + 1
    ranked = []
    for item, terms in zip(docs, vocab):
        common = q & terms
        if not common:
            continue
        score = sum(weight(t) for t in common) / math.sqrt(max(1, len(terms)))
        ranked.append({**item, "score": round(score, 4)})
    return sorted(ranked, key=lambda x: (-x["score"], x["name"]))[:limit]

def plan(task: str, limit: int = 3) -> dict:
    """Build a reviewable sequence, without executing tools or pretending to be an agent."""
    matches = related(task, limit=limit)
    return {
        "task": task,
        "mode": "dry-run",
        "requires_human_approval": True,
        "steps": [
            {"step": i + 1, "skill": match["name"], "action": "review SKILL.md and approve any script execution",
             "reason": match["description"]} for i, match in enumerate(matches)
        ],
        "note": "A deterministic skill plan, not autonomous multi-agent execution.",
    }
