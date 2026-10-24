"""Strict, deterministic v2 project snapshot and immutable scan-policy contracts.

Runtime standard library only. This scanner rejects symlinks/special files rather
than silently following them. On POSIX it opens files using descriptor-relative
NOFOLLOW traversal; concurrent hostile directory mutation is not fully solved.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

VERSION = 2
MAX_FILES = 3000
MAX_FILE_BYTES = 20_000_000
MAX_TOTAL_BYTES = 512_000_000
MAX_LEDGER_BYTES = 10_000_000
MAX_RECORDS = 10_000
ZERO = "0" * 64
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MANDATORY_DIRS = (".git", ".of-provenance", ".omniforge")
DEFAULT_POLICY = {
    "version": 1,
    "exclude_dirs": [".git", ".of-provenance", ".omniforge", ".venv",
                     "node_modules", "__pycache__", ".pytest_cache"],
    "exclude_files": [".env", ".env.*"],
    "max_files": MAX_FILES,
    "max_file_bytes": MAX_FILE_BYTES,
    "max_total_bytes": MAX_TOTAL_BYTES,
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def hashed(domain: bytes, value: Any) -> str:
    return hashlib.sha256(domain + b"\x00" + canonical(value)).hexdigest()


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def parse_json(data: str) -> Any:
    def refuse_constant(value: str):
        raise ValueError("Unsupported JSON constant: " + value)
    return json.loads(data, object_pairs_hook=_unique, parse_constant=refuse_constant)


def validate_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError("Unsafe snapshot relative path")
    if (value.startswith("/") or "\\" in value or "\x00" in value
        or re.match(r"^[A-Za-z]:", value) or unicodedata.normalize("NFC", value) != value):
        raise ValueError("Unsafe snapshot relative path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts) or any(ord(c) < 32 for c in value):
        raise ValueError("Unsafe snapshot relative path")
    if PurePosixPath(value).as_posix() != value:
        raise ValueError("Non-canonical snapshot path")
    return value


def _names(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 64 or len(value) != len(set(
            x for x in value if isinstance(x, str))):
        raise ValueError("Invalid " + label)
    for x in value:
        if not isinstance(x, str) or not x or len(x) > 100 or "/" in x or "\\" in x or x in (".", "..") or "*" in x:
            if label != "exclude_files" or x != ".env.*":
                raise ValueError("Invalid " + label + " item")
    return value


def validate_policy(obj: object) -> dict:
    if not isinstance(obj, dict) or set(obj) != {
        "version", "exclude_dirs", "exclude_files", "max_files",
        "max_file_bytes", "max_total_bytes",
    } or type(obj["version"]) is not int or obj["version"] != 1:
        raise ValueError("Invalid snapshot policy schema")
    dirs = _names(obj["exclude_dirs"], label="exclude_dirs")
    files = _names(obj["exclude_files"], label="exclude_files")
    if not set(MANDATORY_DIRS).issubset(dirs):
        raise ValueError("Mandatory provenance directories cannot be included in a snapshot")
    for key, upper in (("max_files", MAX_FILES), ("max_file_bytes", MAX_FILE_BYTES),
                       ("max_total_bytes", MAX_TOTAL_BYTES)):
        n = obj[key]
        if type(n) is not int or n < 1 or n > upper:
            raise ValueError(f"Invalid {key}: must be within 1..{upper}")
    if obj["max_total_bytes"] < obj["max_file_bytes"]:
        raise ValueError("Total byte limit cannot be smaller than per-file limit")
    return obj


def policy_digest(policy: dict) -> str:
    validate_policy(policy)
    return hashed(b"OF-POLICY-v2", policy)


def snapshot_digest(files: dict[str, str]) -> str:
    if not isinstance(files, dict) or len(files) > MAX_FILES:
        raise ValueError("Invalid number of snapshot files")
    for path, digest in files.items():
        validate_path(path)
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ValueError("Invalid SHA-256 in snapshot")
    return hashed(b"OF-SNAPSHOT-v2", files)


def _matches_file(name: str, patterns: list[str]) -> bool:
    return name in patterns or any(pat.endswith(".*") and
                                    name.startswith(pat[:-1]) for pat in patterns)


def _open_file(root: Path, relative: str):
    """Use openat-style traversal to avoid following replaced intermediate links."""
    parts = relative.split("/")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if os.name != "posix":
        # Windows fallback: path checks cannot eliminate all concurrent swaps.
        from .core import secure_project_path
        path = secure_project_path(root, *parts)
        return os.open(path, os.O_RDONLY | nonblock | nofollow)
    current = os.open(root, os.O_RDONLY | directory | nofollow)
    try:
        for component in parts[:-1]:
            fd = os.open(component, os.O_RDONLY | directory | nofollow, dir_fd=current)
            os.close(current)
            current = fd
        result = os.open(parts[-1], os.O_RDONLY | nofollow | nonblock, dir_fd=current)
        return result
    finally:
        os.close(current)


def scan_project(project: Path, policy: dict) -> dict[str, str]:
    validate_policy(policy)
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project is not a directory")
    files: dict[str, str] = {}
    bytes_scanned = 0
    for parent, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        here = Path(parent)
        kept = []
        for name in sorted(directories):
            if name in policy["exclude_dirs"] or name.startswith(".of-provenance.tmp-"):
                continue
            sub = here / name
            if sub.is_symlink():
                raise ValueError(f"Symlinked project directory: {sub.relative_to(root)}")
            kept.append(name)
        directories[:] = kept
        for name in sorted(filenames):
            if _matches_file(name, policy["exclude_files"]):
                continue
            candidate = here / name
            relative = candidate.relative_to(root).as_posix()
            validate_path(relative)
            if candidate.is_symlink():
                raise ValueError("Symlinked project file: " + relative)
            if len(files) >= policy["max_files"]:
                raise ValueError("Project exceeds max_files")
            fd = _open_file(root, relative)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError("Non-regular project file: " + relative)
                if before.st_size > policy["max_file_bytes"]:
                    raise ValueError("File exceeds max_file_bytes: " + relative)
                digest = hashlib.sha256()
                read = 0
                while True:
                    chunk = os.read(fd, 128 * 1024)
                    if not chunk:
                        break
                    read += len(chunk)
                    if read > policy["max_file_bytes"]:
                        raise ValueError("File grew beyond max_file_bytes: " + relative)
                    digest.update(chunk)
                after = os.fstat(fd)
                if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                     before.st_ctime_ns) !=
                    (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                     after.st_ctime_ns) or read != after.st_size):
                    raise ValueError("Project file changed during snapshot: " + relative)
            finally:
                os.close(fd)
            bytes_scanned += read
            if bytes_scanned > policy["max_total_bytes"]:
                raise ValueError("Project exceeds max_total_bytes")
            files[relative] = digest.hexdigest()
    return dict(sorted(files.items()))
