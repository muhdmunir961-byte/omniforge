"""Token-frugal router: select metadata first, open full skill only on demand."""
from __future__ import annotations

import hashlib
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


def load_skill(name: str, *, max_chars: int = 12000,
               known_sha256: str | None = None) -> dict:
    """Load one skill; a matching caller digest suppresses duplicate content."""
    if name not in bundled_names():
        raise ValueError(f"Unknown skill: {name}")
    if known_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", known_sha256):
        raise ValueError("known_sha256 must be a lowercase SHA-256 digest")
    doc = (bundled_root() / name / "SKILL.md").read_text(encoding="utf-8")
    if len(doc) > max_chars:
        raise ValueError(f"Skill requires {len(doc)} characters, exceeds --max-chars {max_chars}")
    digest = hashlib.sha256(doc.encode("utf-8")).hexdigest()
    unchanged = digest == known_sha256
    return {"name": name, "content": "" if unchanged else doc,
            "sha256": digest, "status": "unchanged" if unchanged else "changed",
            "characters": len(doc),
            "estimated_tokens": 0 if unchanged else estimate_tokens(doc)}


def estimate_tokens(text: str) -> int:
    """Rough char-based estimate, not provider tokenizer billing information."""
    return math.ceil(len(text) / 4)


def token_report(*, chosen: str | None = None) -> dict:
    summaries = index()
    compact = "\n".join(f'{s["name"]}: {s["description"]}' for s in summaries)
    # Estimate total bytes by filesystem metadata; do not re-open every SKILL.md.
    # UTF-8 byte lengths can differ from character counts, hence only an estimate.
    total_bytes = sum((bundled_root() / s["name"] / "SKILL.md").stat().st_size for s in summaries)
    loaded = load_skill(chosen)["content"] if chosen else ""
    return {
        "skill_count": len(summaries), "metadata_estimated_tokens": estimate_tokens(compact),
        "load_everything_estimated_tokens": math.ceil((total_bytes + max(0, len(summaries) - 1)) / 4),
        "on_demand_estimated_tokens": estimate_tokens(compact + loaded),
        "selected": chosen, "notice": "Approximate UTF-8 byte/character heuristic; not provider-billed tokens. No full-skill-content cache is maintained.",
    }
