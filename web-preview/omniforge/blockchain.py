"""Opt-in provenance blockchain: local hash-chain with optional EVM anchoring.

Local records are tamper-evident only when their head hash is trusted outside
the mutable ledger (for example, anchored on-chain). This is not a consensus
network, a cryptocurrency, a digital signature, or a wallet.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .core import secure_project_path
from .provenance import build_manifest

ZERO = "0" * 64
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")
MAX_BYTES = 10_000_000
MAX_RECORDS = 10_000


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def ledger_path(project: Path) -> Path:
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project must be a directory")
    return secure_project_path(root, ".omniforge", "chain.jsonl")


def snapshot(project: Path) -> tuple[str, int]:
    manifest = build_manifest(project)
    return digest(manifest), len(manifest["files"])


def _read(data: str) -> list[dict]:
    if len(data.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Blockchain ledger exceeds 10 MB limit")
    if data and not data.endswith("\n"):
        raise ValueError("Ledger has an incomplete trailing record")
    records = []
    parent = ZERO
    required = {"version", "height", "timestamp", "previous", "snapshot", "files", "note", "hash"}
    for line in data.splitlines():
        if not line:
            raise ValueError("Ledger contains an empty record")
        try:
            block = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("Ledger contains invalid JSON") from exc
        if not isinstance(block, dict) or set(block) != required:
            raise ValueError("Invalid ledger record structure")
        height = len(records)
        if (type(block["version"]) is not int or block["version"] != 1
            or type(block["height"]) is not int or block["height"] != height
            or type(block["files"]) is not int or not 0 <= block["files"] <= 3000
            or not isinstance(block["note"], str) or len(block["note"]) > 160
            or not isinstance(block["timestamp"], str)
            or not isinstance(block["previous"], str) or block["previous"] != parent
            or not isinstance(block["snapshot"], str) or not DIGEST.fullmatch(block["snapshot"])
            or not isinstance(block["hash"], str) or not DIGEST.fullmatch(block["hash"])):
            raise ValueError(f"Invalid ledger metadata or broken link at height {height}")
        try:
            timestamp = datetime.fromisoformat(block["timestamp"])
            if timestamp.tzinfo is None:
                raise ValueError("Timezone required")
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp at height {height}") from exc
        payload = {k: v for k, v in block.items() if k != "hash"}
        if block["hash"] != digest(payload):
            raise ValueError(f"Tampered ledger record at height {height}")
        parent = block["hash"]
        records.append(block)
        if len(records) > MAX_RECORDS:
            raise ValueError("Ledger exceeds record limit")
    return records


@contextmanager
def _locked_ledger(project: Path, create: bool):
    """Lock local file while reading/appending; fail closed if no locker exists."""
    path = ledger_path(project)
    if create:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = ledger_path(project)  # re-check after creating parents
    elif not path.is_file():
        raise ValueError("Ledger does not exist; record an entry first")
    flags = os.O_RDWR | (os.O_CREAT if create else 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        if os.name == "posix":
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        elif os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            raise ValueError("Filesystem locking unavailable on this platform")
        with os.fdopen(fd, "r+", encoding="utf-8", newline="\n") as stream:
            fd = -1
            yield stream
    finally:
        if fd >= 0:
            os.close(fd)


def _entries(project: Path) -> list[dict]:
    with _locked_ledger(project, create=False) as stream:
        return _read(stream.read())


def record(project: Path, note: str = "") -> dict:
    if not isinstance(note, str) or len(note) > 160 or any(ord(c) < 32 for c in note):
        raise ValueError("Note must be a short single-line string (max 160 characters)")
    root = project.expanduser().resolve(strict=True)
    with _locked_ledger(root, create=True) as stream:
        entries = _read(stream.read())
        if len(entries) >= MAX_RECORDS:
            raise ValueError("Ledger is full")
        snapshot_hash, files = snapshot(root)
        payload = {
            "version": 1,
            "height": len(entries),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous": entries[-1]["hash"] if entries else ZERO,
            "snapshot": snapshot_hash,
            "files": files,
            "note": note,
        }
        block = {**payload, "hash": digest(payload)}
        line = canonical(block).decode("utf-8") + "\n"
        if stream.tell() + len(line.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Ledger exceeds 10 MB limit")
        stream.seek(0, os.SEEK_END)
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
        return block


def verify(project: Path, *, check_current: bool = False) -> dict:
    root = project.expanduser().resolve(strict=True)
    try:
        entries = _entries(root)
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    if not entries:
        return {"ok": False, "error": "Ledger is empty"}
    result = {
        "ok": True, "entries": len(entries), "height": entries[-1]["height"],
        "head": entries[-1]["hash"], "local_only": True,
        "note": "A rewritable local hash-chain is NOT a decentralized or signed blockchain.",
    }
    if check_current:
        current, _ = snapshot(root)
        result["current_snapshot_match"] = current == entries[-1]["snapshot"]
        result["ok"] = result["current_snapshot_match"]
    return result


def proof(project: Path, height: int | None = None) -> dict:
    entries = _entries(project)
    if not entries:
        raise ValueError("Ledger is empty")
    if height is None:
        height = len(entries) - 1
    if type(height) is not int or not 0 <= height < len(entries):
        raise ValueError("Invalid ledger height")
    return dict(entries[height])


def anchor_payload(project: Path, *, address: str, chain_id: int,
                   height: int | None = None) -> dict:
    """Unsigned self-transaction with 32-byte SHA-256 digest as EVM calldata."""
    if not isinstance(address, str) or not ADDRESS.fullmatch(address) or int(address[2:], 16) == 0:
        raise ValueError("A nonzero EVM wallet address (0x + 40 hex) is required")
    if type(chain_id) is not int or not 1 <= chain_id < 2**53:
        raise ValueError("chain_id must be a positive integer")
    block = proof(project, height)
    transaction = {
        "from": address, "to": address, "value": "0x0",
        "data": "0x" + block["hash"], "chainId": hex(chain_id),
    }
    return {
        "height": block["height"], "ledger_hash": block["hash"],
        "unsigned_transaction": transaction,
        "status": "wallet-signature-required",
        "warning": "No transaction was submitted. A wallet must approve network gas fees. "
                   "Anchoring proves this hash was recorded in a confirmed transaction, "
                   "not who originally authored the files.",
    }
