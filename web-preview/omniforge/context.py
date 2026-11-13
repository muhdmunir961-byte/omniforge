"""Bounded, conditional source reads for coding agents; no persistent content cache.

This command only reads one explicitly named local source file. It never uploads
content, follows symlinks, walks the project, or stores file bodies. Agents must
still avoid selecting credential-bearing source and treat excerpts as untrusted.
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

SOURCE_EXTENSIONS = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java", ".c",
    ".cc", ".cpp", ".h", ".hpp", ".css", ".html", ".md", ".json",
    ".yml", ".yaml", ".toml", ".sh",
})
SKIP_PARTS = frozenset({
    "node_modules", "vendor", "dist", "build", "target", "coverage",
    "__pycache__", ".git", "secrets", "credentials",
})
MAX_FILE_BYTES = 256_000


def read_context(project: Path, path: str, *, known_sha256: str | None = None,
                 start_line: int = 1, max_lines: int = 100,
                 max_chars: int = 6000) -> dict:
    """Read a small, line-numbered excerpt; omit content if digest matches.

    The digest is supplied by the caller, not kept in server memory.
    Hashing the local file checks freshness; no claim is made that storage I/O
    or provider-side context caching is eliminated.
    """
    if known_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", known_sha256):
        raise ValueError("known_sha256 must be a lowercase SHA-256 digest")
    if type(start_line) is not int or start_line < 1:
        raise ValueError("start_line must be positive")
    if type(max_lines) is not int or not 1 <= max_lines <= 160:
        raise ValueError("max_lines must be 1..160")
    if type(max_chars) is not int or not 256 <= max_chars <= 12000:
        raise ValueError("max_chars must be 256..12000")
    if (not isinstance(path, str) or len(path) > 1024 or not path
            or "\\" in path or "\x00" in path):
        raise ValueError("Specify one safe relative source path")
    parts = path.split("/")
    if any(not part or part in {".", ".."} or part.startswith(".")
           or part.lower() in SKIP_PARTS for part in parts):
        raise ValueError("Hidden, generated, credential, or traversal paths are not supported")
    if Path(path).is_absolute() or Path(path).suffix.lower() not in SOURCE_EXTENSIONS:
        raise ValueError("Unsupported source path or extension")
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project must be an existing directory")
    target = root
    for part in parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("Symlinked paths are not supported")
    if not target.is_file() or not target.resolve().is_relative_to(root):
        raise ValueError("Source file must exist inside the project")
    with target.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Source exceeds 256 KB; request a narrower file")
    digest = hashlib.sha256(data).hexdigest()
    response = {"path": "/".join(parts), "sha256": digest}
    if digest == known_sha256:
        return {**response, "status": "unchanged", "content": "",
                "estimated_tokens": 0, "next_line": None}
    source = data.decode("utf-8")
    lines = source.splitlines()
    if start_line > len(lines) and lines:
        raise ValueError("start_line exceeds source line count")
    output = []
    used = 0
    for number, line in enumerate(lines[start_line - 1:start_line - 1 + max_lines], start_line):
        rendered = f"{number}: {line}"
        if used + len(rendered) + (1 if output else 0) > max_chars:
            if not output:
                raise ValueError("Line exceeds max_chars; choose a larger limit or shorter source")
            break
        output.append(rendered)
        used += len(rendered) + (1 if len(output) > 1 else 0)
    last = start_line + len(output) - 1
    return {**response, "status": "changed",
            "content": "\n".join(output), "start_line": start_line,
            "end_line": last, "total_lines": len(lines),
            "next_line": last + 1 if last < len(lines) else None,
            "estimated_tokens": math.ceil(used / 4),
            "notice": "Heuristic excerpt size, not provider-billed tokens. No content is cached."}
