"""Deterministic local SHA-256 manifest; unsigned (not supply-chain attestation)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXCLUDE = {'.git', '.omniforge', '.of-provenance', '.venv', '__pycache__', 'node_modules', '.pytest_cache'}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(128*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(project: Path, *, limit: int = 3000) -> dict:
    root = project.resolve()
    entries = {}
    for p in root.rglob('*'):
        rel = p.relative_to(root)
        if any(x in EXCLUDE for x in rel.parts) or p.name == 'omniforge-manifest.json' or p.is_symlink() or not p.is_file():
            continue
        if p.stat().st_size > 20_000_000:
            continue
        entries[rel.as_posix()] = _hash(p)
        if len(entries) > limit:
            raise ValueError('Too many files; narrow the project')
    return {'format': 'omniforge-sha256-v1', 'signed': False, 'files': dict(sorted(entries.items()))}


def check_manifest(project: Path, manifest_path: Path) -> dict:
    root = project.resolve()
    obj = json.loads(manifest_path.read_text(encoding='utf-8'))
    if obj.get('format') != 'omniforge-sha256-v1' or not isinstance(obj.get('files'), dict):
        raise ValueError('Unsupported hash manifest')
    changed, missing = [], []
    for rel, expected in obj['files'].items():
        if not isinstance(rel, str) or not isinstance(expected, str) or len(expected) != 64:
            raise ValueError('Invalid manifest entry')
        p = (root / rel).resolve()
        if not p.is_relative_to(root) or p.is_symlink():
            raise ValueError('Manifest contains an unsafe path')
        if not p.is_file():
            missing.append(rel)
        elif _hash(p) != expected:
            changed.append(rel)
    return {'ok': not (changed or missing), 'checked': len(obj['files']),
            'changed':changed, 'missing':missing, 'signed':False,
            'note':'Hash integrity check, not cryptographic identity or provenance certification.'}
