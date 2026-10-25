"""Hybrid lexical retrieval with optional locally installed sentence embeddings.

Never downloads a model automatically. Embeddings require an already available
local model and the optional sentence-transformers dependency.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from .router import index, tokens

ALIASES = {
    'errors': ('log', 'triage', 'debug'), 'crash': ('log', 'triage'),
    'bug': ('debug', 'diff'), 'database': ('sqlite', 'schema'),
    'api': ('http', 'openapi', 'probe'), 'endpoints': ('openapi', 'api'),
    'arduino': ('firmware', 'esp32'), 'hardware': ('firmware', 'esp32'),
    'credentials': ('secret', 'hygiene'), 'password': ('secret', 'hygiene'),
    'dependencies': ('dependency', 'inventory'), 'package': ('dependency', 'inventory'),
    'functions': ('python', 'symbols'), 'refactor': ('python', 'symbols', 'diff'),
    'vulnerabilities': ('trivy', 'security'), 'pcb': ('kicad', 'drc'),
    'browser': ('playwright', 'snapshot'), 'testing': ('test', 'audit'),
}


def _expand(values: set[str]) -> set[str]:
    expanded = set(values)
    for value in values:
        for alias in ALIASES.get(value, ()):
            expanded.add(alias)
    return expanded


def _trigrams(value: str) -> set[str]:
    text = '  ' + re.sub(r'[^a-z0-9 ]', ' ', value.lower()) + '  '
    return {text[i:i+3] for i in range(max(0, len(text) - 2))}


def hybrid_search(query: str, limit: int = 5) -> list[dict]:
    """Deterministic local fuzzy retrieval; no API cost, not neural semantics."""
    if not 1 <= limit <= 20:
        raise ValueError('limit must be between 1 and 20')
    if not query.strip():
        return index()[:limit]
    entries = index()
    qwords = _expand(tokens(query))
    qgrams = _trigrams(query)
    docs = [tokens(item['name'].replace('-', ' ') + ' ' + item['description']) for item in entries]
    document_freq = Counter(word for terms in docs for word in terms)
    ranked = []
    for item, terms in zip(entries, docs):
        overlap = qwords & terms
        weighted = sum(math.log(1 + (len(entries) + 1)/(document_freq[w] + 1)) for w in overlap)
        name_terms = tokens(item['name'].replace('-', ' '))
        title_match = 2.0 * len(name_terms & qwords)
        grams = _trigrams(item['name'] + ' ' + item['description'])
        gram_sim = len(qgrams & grams) / max(1, len(qgrams | grams))
        score = weighted + title_match + gram_sim
        if score > .035:
            ranked.append(dict(item, score=round(score, 5), method='local-hybrid'))
    return sorted(ranked, key=lambda e: (-e['score'], e['name']))[:limit]


def embedding_search(query: str, *, model_path: str, limit: int = 5) -> list[dict]:
    """Opt-in neural search. Model path must be already available locally."""
    from pathlib import Path
    if not 1 <= limit <= 20:
        raise ValueError('limit must be between 1 and 20')
    if not Path(model_path).expanduser().is_dir():
        raise ValueError('Local embedding model directory does not exist; no model is auto-downloaded')
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise ValueError('Optional sentence-transformers is not installed') from exc
    model = SentenceTransformer(str(Path(model_path).expanduser().resolve()), local_files_only=True)
    entries = index()
    texts = [f"{entry['name']}: {entry['description']}" for entry in entries]
    vectors = model.encode([query] + texts, normalize_embeddings=True)
    scores = []
    for item, vector in zip(entries, vectors[1:]):
        score = float(sum(float(a)*float(b) for a, b in zip(vectors[0], vector)))
        scores.append(dict(item, score=round(score, 5), method='local-embeddings'))
    return sorted(scores, key=lambda e: (-e['score'], e['name']))[:limit]
