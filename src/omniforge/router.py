"""Token-frugal router: select metadata first, open full skill only on demand."""
from __future__ import annotations

import math
import re
from pathlib import Path
from .core import bundled_root, bundled_names, skill_info

STOP = frozenset("a an and are at be by for from how i in is it of on or our the this to use we with you your my me do help can please yang dan untuk dari cara aku nak dalam buat guna pakai".split())


def tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z][a-z0-9_-]{1,}", text.lower()) if x not in STOP}


def index(paths: list[Path] | None = None) -> list[dict]:
    dirs = paths if paths is not None else [bundled_root() / name for name in bundled_names()]
    result = []
    for path in dirs:
        try:
            result.append(skill_info(path))
        except (OSError, ValueError):
            continue
    return result


def search_skills(query: str, *, limit: int = 5, paths: list[Path] | None = None) -> list[dict]:
    entries = index(paths)
    if not query.strip():
        return entries[:limit]
    words = tokens(query)
    scored = []
    for info in entries:
        title_words = tokens(info["name"].replace("-", " "))
        desc_words = tokens(info["description"])
        overlap = words & (title_words | desc_words)
        score = 5 * len(words & title_words) + len(words & desc_words)
        if query.lower() in info["description"].lower():
            score += 2
        if score > 0:
            scored.append((score / math.sqrt(1 + len(desc_words)), info))
    return [dict(info, score=round(score, 3)) for score, info in sorted(scored, key=lambda x: (-x[0], x[1]["name"]))[:limit]]


def load_skill(name: str, *, max_chars: int = 12000) -> dict:
    """Only the requested skill is expanded; never silently concatenate skills."""
    if name not in bundled_names():
        raise ValueError(f"Unknown skill: {name}")
    doc = (bundled_root() / name / "SKILL.md").read_text(encoding="utf-8")
    if len(doc) > max_chars:
        raise ValueError(f"Skill requires {len(doc)} characters, exceeds --max-chars {max_chars}")
    return {"name": name, "content": doc, "characters": len(doc), "estimated_tokens": estimate_tokens(doc)}


def estimate_tokens(text: str) -> int:
    """Rough char-based estimate, not provider tokenizer billing information."""
    return math.ceil(len(text) / 4)


def token_report(*, chosen: str | None = None) -> dict:
    summaries = index()
    compact = "\n".join(f'{s["name"]}: {s["description"]}' for s in summaries)
    naive = "\n".join((bundled_root() / s["name"] / "SKILL.md").read_text(encoding="utf-8") for s in summaries)
    loaded = load_skill(chosen)["content"] if chosen else ""
    return {
        "skill_count": len(summaries), "metadata_estimated_tokens": estimate_tokens(compact),
        "load_everything_estimated_tokens": estimate_tokens(naive),
        "on_demand_estimated_tokens": estimate_tokens(compact + loaded),
        "selected": chosen, "notice": "Approximate character heuristic, not measured model usage. VS Code/client may add context independently.",
    }
