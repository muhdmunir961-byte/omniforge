"""OF-Provenance v2: strict ledger, historical policies, trusted checkpoints.

Separate from the backwards-compatible legacy blockchain command.
No wallet keys, signing, broadcast or third-party network operations.
"""
from __future__ import annotations
import hashlib
import os
import re
import stat
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .core import secure_project_path
from .provenance_v2_policy import (
    DEFAULT_POLICY, HEX64, MAX_LEDGER_BYTES, MAX_RECORDS, VERSION, ZERO,
    canonical, hashed, parse_json, policy_digest, scan_project, snapshot_digest,
    validate_policy,
)

STATE = ".of-provenance"
UTC_PATTERN = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z\Z")
REQUIRED = frozenset({
    "version", "seq", "timestamp", "project_id", "file_hashes",
    "snapshot_hash", "policy", "policy_hash", "prev_hash",
    "entry_hash", "anchor_status",
})
ALLOWED = REQUIRED | {"note", "legacy_ref"}
LEGACY_KEYS = {"head", "ledger_sha256", "entries", "anchors_sha256"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def root_path(project: Path) -> Path:
    root = Path(project).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project must be a directory")
    return root


def local_path(root: Path, name: str) -> Path:
    return secure_project_path(root, STATE, name)


def read_safe(path: Path, limit: int = MAX_LEDGER_BYTES) -> bytes:
    if path.is_symlink():
        raise ValueError("Provenance file is a symlink")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise ValueError("Provenance file is not regular or is too large")
        parts = []
        total = 0
        while True:
            chunk = os.read(fd, min(128 * 1024, limit + 1 - total))
            if not chunk:
                break
            parts.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ValueError("Provenance file exceeds size limit")
        return b"".join(parts)
    finally:
        os.close(fd)


def create_safe(path: Path, value: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def check_project_id(value: object):
    try:
        parsed = uuid.UUID(value) if isinstance(value, str) else None
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid project_id UUID") from exc
    if parsed is None or parsed.version != 4 or str(parsed) != value:
        raise ValueError("Expected canonical project_id UUIDv4")


def check_legacy_shape(ref: object):
    if not isinstance(ref, dict) or set(ref) != LEGACY_KEYS:
        raise ValueError("Invalid legacy link schema")
    if (any(not isinstance(ref[k], str) or not HEX64.fullmatch(ref[k])
            for k in ("head", "ledger_sha256"))
        or type(ref["entries"]) is not int or not 1 <= ref["entries"] <= MAX_RECORDS
        or (ref["anchors_sha256"] is not None and
            (not isinstance(ref["anchors_sha256"], str) or
             not HEX64.fullmatch(ref["anchors_sha256"])))):
        raise ValueError("Invalid legacy link fields")


def strict_legacy(raw: bytes) -> list[dict]:
    try:
        data = raw.decode("utf-8")
        if not data or not data.endswith("\n"):
            raise ValueError("Legacy JSONL is empty or incomplete")
        for line in data.splitlines():
            parse_json(line)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid legacy JSONL") from exc
    from .blockchain import _read as v1_parse
    entries = v1_parse(data)
    if not entries:
        raise ValueError("Legacy ledger is empty")
    return entries


def check_legacy(root: Path, ref: dict | None):
    if ref is None:
        return
    check_legacy_shape(ref)
    raw = read_safe(local_path(root, "legacy-v1-chain.jsonl"))
    if hashlib.sha256(raw).hexdigest() != ref["ledger_sha256"]:
        raise ValueError("Legacy archive digest mismatch")
    entries = strict_legacy(raw)
    if len(entries) != ref["entries"] or entries[-1]["hash"] != ref["head"]:
        raise ValueError("Legacy head mismatch")
    if ref["anchors_sha256"] is not None:
        raw = read_safe(local_path(root, "legacy-v1-anchors.jsonl"))
        if hashlib.sha256(raw).hexdigest() != ref["anchors_sha256"]:
            raise ValueError("Legacy anchors archive digest mismatch")


def config_for(root: Path) -> dict:
    try:
        cfg = parse_json(read_safe(local_path(root, "config.json"), 32_000).decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Invalid provenance config") from exc
    if not isinstance(cfg, dict) or set(cfg) != {
        "version", "project_id", "policy", "legacy_ref",
    } or type(cfg["version"]) is not int or cfg["version"] != VERSION:
        raise ValueError("Unsupported provenance config schema")
    check_project_id(cfg["project_id"])
    validate_policy(cfg["policy"])
    if cfg["legacy_ref"] is not None:
        check_legacy_shape(cfg["legacy_ref"])
    return cfg


def init(project: Path, *, legacy: dict | None = None,
         old_chain: bytes | None = None, old_anchors: bytes | None = None) -> dict:
    root = root_path(project)
    state = root / STATE
    if state.exists() or state.is_symlink():
        raise ValueError("Provenance state already exists; refusing overwrite")
    if legacy is None and (root / ".omniforge" / "chain.jsonl").exists():
        raise ValueError("Legacy v1 ledger present: run migrate --approve")
    if legacy is not None:
        check_legacy_shape(legacy)
        if old_chain is None or hashlib.sha256(old_chain).hexdigest() != legacy["ledger_sha256"]:
            raise ValueError("Invalid legacy source backup")
    state.mkdir(mode=0o700)
    cfg = {
        "version": VERSION, "project_id": str(uuid.uuid4()),
        "policy": parse_json(canonical(DEFAULT_POLICY).decode("utf-8")),
        "legacy_ref": legacy,
    }
    create_safe(local_path(root, "config.json"), canonical(cfg) + b"\n")
    create_safe(local_path(root, "chain.jsonl"), b"")
    create_safe(local_path(root, "anchors.jsonl"), b"")
    create_safe(local_path(root, "lock"), b"0")
    if legacy is not None:
        create_safe(local_path(root, "legacy-v1-chain.jsonl"), old_chain)
        if old_anchors is not None:
            create_safe(local_path(root, "legacy-v1-anchors.jsonl"), old_anchors)
    return {"status": "initialized", "version": VERSION,
            "project_id": cfg["project_id"], "legacy_ref": legacy}


def migrate(project: Path, *, approve: bool = False) -> dict:
    """Copy, NEVER rewrite, validated v1 records and anchor metadata."""
    root = root_path(project)
    if (root / STATE).exists() or (root / STATE).is_symlink():
        raise ValueError("v2 state already exists; migration is not an overwrite")
    old = secure_project_path(root, ".omniforge", "chain.jsonl")
    if not old.is_file():
        raise ValueError("No old v1 chain.jsonl")
    raw = read_safe(old)
    entries = strict_legacy(raw)
    path = secure_project_path(root, ".omniforge", "anchors.jsonl")
    if path.is_symlink():
        raise ValueError("Legacy anchor metadata cannot be symlinked")
    anchors = read_safe(path) if path.is_file() else None
    ref = {
        "head": entries[-1]["hash"],
        "ledger_sha256": hashlib.sha256(raw).hexdigest(),
        "entries": len(entries),
        "anchors_sha256": hashlib.sha256(anchors).hexdigest() if anchors is not None else None,
    }
    if not approve:
        return {"status": "preview-only", "requires_approval": True,
                "legacy_ref": ref, "note": "Copy-only; old files remain intact"}
    result = init(root, legacy=ref, old_chain=raw, old_anchors=anchors)
    result["status"] = "migrated"
    result["note"] = "Use snapshot to create a new v2 genesis linking the v1 head"
    return result


@contextmanager
def locked(root: Path):
    fd = os.open(local_path(root, "lock"),
                 os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    try:
        if os.name == "posix":
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        elif os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            raise ValueError("Filesystem locking not available")
        yield
    finally:
        os.close(fd)


def check_entry(item: object, seq: int, previous: str, project_id: str):
    if not isinstance(item, dict) or not REQUIRED.issubset(item) or not set(item).issubset(ALLOWED):
        raise ValueError(f"Unexpected ledger fields at seq={seq}")
    if (type(item["version"]) is not int or item["version"] != VERSION
        or type(item["seq"]) is not int or item["seq"] != seq
        or item["project_id"] != project_id
        or item["anchor_status"] != "not_requested"):
        raise ValueError(f"Invalid ledger metadata at seq={seq}")
    check_project_id(item["project_id"])
    stamp = item["timestamp"]
    if not isinstance(stamp, str) or not UTC_PATTERN.fullmatch(stamp):
        raise ValueError("Invalid UTC timestamp")
    try:
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp date") from exc
    if "note" in item and (not isinstance(item["note"], str) or len(item["note"]) > 160
                           or any(ord(c) < 32 for c in item["note"])):
        raise ValueError("Invalid ledger note")
    if "legacy_ref" in item:
        if seq != 0:
            raise ValueError("Legacy link is allowed only on genesis record")
        check_legacy_shape(item["legacy_ref"])
    if not isinstance(item["policy"], dict):
        raise ValueError("Missing historical policy object")
    if item["policy_hash"] != policy_digest(item["policy"]):
        raise ValueError("Historic policy hash mismatch")
    if item["snapshot_hash"] != snapshot_digest(item["file_hashes"]):
        raise ValueError("Snapshot hash mismatch")
    if item["prev_hash"] != previous:
        raise ValueError("Broken prev_hash")
    expected = hashed(b"OF-ENTRY-v2",
                      {key: val for key, val in item.items() if key != "entry_hash"})
    if not isinstance(item["entry_hash"], str) or not HEX64.fullmatch(item["entry_hash"]) or item["entry_hash"] != expected:
        raise ValueError("Ledger entry hash mismatch")


def read_entries(root: Path, config: dict) -> list[dict]:
    raw = read_safe(local_path(root, "chain.jsonl"))
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Ledger ends with incomplete JSONL record")
    try:
        items = [parse_json(line) for line in raw.decode("utf-8").splitlines()]
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid JSONL or duplicate JSON key") from exc
    if len(items) > MAX_RECORDS:
        raise ValueError("Ledger exceeds MAX_RECORDS")
    previous = ZERO
    for seq, item in enumerate(items):
        check_entry(item, seq, previous, config["project_id"])
        previous = item["entry_hash"]
    if items and items[0].get("legacy_ref") != config["legacy_ref"]:
        raise ValueError("Legacy head/genesis link mismatch")
    check_legacy(root, config["legacy_ref"])
    return items


def snapshot(project: Path, *, note: str = "", allow_policy_change: bool = False,
             expected_head: str | None = None) -> dict:
    root = root_path(project)
    if not isinstance(note, str) or len(note) > 160 or any(ord(c) < 32 for c in note):
        raise ValueError("Invalid note; never include secrets")
    if expected_head is not None and (not isinstance(expected_head, str)
                                     or not HEX64.fullmatch(expected_head)):
        raise ValueError("Invalid expected head")
    with locked(root):
        cfg = config_for(root)
        items = read_entries(root, cfg)
        _anchor_events(root, items)
        if len(items) >= MAX_RECORDS:
            raise ValueError("Ledger full; archive and re-initialize a new project instead of truncating")
        head = items[-1]["entry_hash"] if items else ZERO
        if expected_head is not None and head != expected_head:
            raise ValueError("Expected head mismatch")
        policy = cfg["policy"]
        if items and items[-1]["policy_hash"] != policy_digest(policy) and not allow_policy_change:
            raise ValueError("Policy changed: explicit --allow-policy-change required")
        found = scan_project(root, policy)
        payload = {
            "version": VERSION, "seq": len(items), "timestamp": utc_now(),
            "project_id": cfg["project_id"], "file_hashes": found,
            "snapshot_hash": snapshot_digest(found), "policy": policy,
            "policy_hash": policy_digest(policy), "prev_hash": head,
            "anchor_status": "not_requested",
        }
        if note:
            payload["note"] = note
        if not items and cfg["legacy_ref"] is not None:
            payload["legacy_ref"] = cfg["legacy_ref"]
        item = {**payload, "entry_hash": hashed(b"OF-ENTRY-v2", payload)}
        line = canonical(item) + b"\n"
        path = local_path(root, "chain.jsonl")
        if path.stat().st_size + len(line) > MAX_LEDGER_BYTES:
            raise ValueError("Ledger exceeds 10 MB: do not silently delete history")
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0))
        try:
            if os.write(fd, line) != len(line):
                raise OSError("Partial provenance ledger append")
            os.fsync(fd)
        finally:
            os.close(fd)
        return {"status": "recorded", "seq": item["seq"], "entry_hash": item["entry_hash"],
                "snapshot_hash": item["snapshot_hash"], "policy_hash": item["policy_hash"],
                "files": len(found)}


def _anchor_events(root: Path, items: list[dict]) -> list[dict]:
    """Local journal integrity only; it is NOT evidence of current RPC validity."""
    raw = read_safe(local_path(root, "anchors.jsonl"))
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Truncated anchor evidence log")
    try:
        events = [parse_json(line) for line in raw.decode("utf-8").splitlines()]
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid anchor evidence JSONL") from exc
    if len(events) > MAX_RECORDS:
        raise ValueError("Too many anchor evidence records")
    from .blockchain import ADDRESS
    from .evm import TXID
    previous = ZERO
    required = {"version", "seq", "entry_hash", "tx_hash", "wallet", "chain_id",
                "confirmations", "checked_at", "status", "prev_event_hash", "event_hash"}
    for event in events:
        if not isinstance(event, dict) or set(event) != required:
            raise ValueError("Invalid anchor evidence schema")
        index = event["seq"]
        if (type(event["version"]) is not int or event["version"] != 2
            or type(index) is not int or index < 0 or index >= len(items)
            or event["entry_hash"] != items[index]["entry_hash"]
            or not isinstance(event["tx_hash"], str) or not TXID.fullmatch(event["tx_hash"])
            or not isinstance(event["wallet"], str) or not ADDRESS.fullmatch(event["wallet"])
            or not int(event["wallet"][2:], 16)
            or type(event["chain_id"]) is not int or not 1 <= event["chain_id"] < 2**53
            or type(event["confirmations"]) is not int or event["confirmations"] < 1
            or event["status"] != "verified_via_rpc_at_time"
            or not isinstance(event["checked_at"], str)
            or not UTC_PATTERN.fullmatch(event["checked_at"])
            or event["prev_event_hash"] != previous
            or event["event_hash"] != hashed(
                b"OF-ANCHOR-EVENT-v2",
                {k: v for k, v in event.items() if k != "event_hash"}
            )):
            raise ValueError("Invalid/tampered anchor evidence event")
        try:
            datetime.fromisoformat(event["checked_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid anchor journal date") from exc
        previous = event["event_hash"]
    return events


def save_rpc_receipt(project: Path, report: dict, *, wallet: str) -> dict:
    """Persist a locally untrusted time-of-check record after explicit RPC verification."""
    from .blockchain import ADDRESS
    if not isinstance(wallet, str) or not ADDRESS.fullmatch(wallet):
        raise ValueError("Invalid public wallet")
    if report.get("ok") is not True:
        raise ValueError("Only successful RPC verification can be journaled")
    root = root_path(project)
    with locked(root):
        items = read_entries(root, config_for(root))
        seq = report.get("seq")
        if type(seq) is not int or not 0 <= seq < len(items):
            raise ValueError("Invalid anchor sequence")
        if items[seq]["entry_hash"] != report.get("entry_hash"):
            raise ValueError("Ledger changed between RPC check and saving receipt")
        events = _anchor_events(root, items)
        payload = {
            "version": 2, "seq": seq, "entry_hash": report["entry_hash"],
            "tx_hash": report["tx_hash"], "wallet": wallet,
            "chain_id": report["chain_id"],
            "confirmations": report["confirmations"], "checked_at": utc_now(),
            "status": "verified_via_rpc_at_time",
            "prev_event_hash": events[-1]["event_hash"] if events else ZERO,
        }
        event = {**payload, "event_hash": hashed(b"OF-ANCHOR-EVENT-v2", payload)}
        line = canonical(event) + b"\n"
        path = local_path(root, "anchors.jsonl")
        if path.stat().st_size + len(line) > MAX_LEDGER_BYTES:
            raise ValueError("Anchor evidence log full")
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0))
        try:
            if os.write(fd, line) != len(line):
                raise OSError("Partial anchor journal write")
            os.fsync(fd)
        finally:
            os.close(fd)
        return {"status": "journaled-local-only", "event_hash": event["event_hash"],
                "warning": "Stored RPC response is NOT current on-chain proof; verify again."}


def differences(old: dict, new: dict) -> dict:
    a, b = set(old), set(new)
    return {"missing": sorted(a - b), "added": sorted(b - a),
            "modified": sorted(key for key in a & b if old[key] != new[key])}


def verify(project: Path, *, check_files: bool = False,
           expected_head: str | None = None, expected_seq: int | None = None) -> dict:
    if (expected_head is None) != (expected_seq is None):
        raise ValueError("Both expected_head and expected_seq required for checkpoint")
    if expected_head is not None and (
        not isinstance(expected_head, str) or not HEX64.fullmatch(expected_head)
        or type(expected_seq) is not int or expected_seq < 0
    ):
        raise ValueError("Invalid trusted checkpoint")
    root = root_path(project)
    try:
        with locked(root):
            cfg = config_for(root)
            items = read_entries(root, cfg)
            if not items:
                return {"ok": False, "reason": "empty-ledger"}
            events = _anchor_events(root, items)
            tip = items[-1]
            report = {
                "ok": True, "seq": tip["seq"], "entries": len(items),
                "head": tip["entry_hash"], "project_id": cfg["project_id"],
                "anchor_evidence_events": len(events),
                "anchor_evidence_note": "Historical untrusted RPC claims only; re-verify on chain.",
                "trusted_checkpoint": expected_head is not None,
                "policy_history": [
                    {"seq": row["seq"], "policy_hash": row["policy_hash"]}
                    for row in items
                ],
                "warning": "Full local history can be rewritten without an external trusted head.",
            }
            if expected_head is not None:
                if expected_seq >= len(items) or items[expected_seq]["entry_hash"] != expected_head:
                    report.update({"ok": False, "reason": "trusted-checkpoint-mismatch"})
                    return report
            if check_files:
                diff = differences(tip["file_hashes"], scan_project(root, tip["policy"]))
                changed = cfg["policy"] != tip["policy"]
                report.update({"files": diff, "policy_changed": changed})
                report["ok"] = not any(diff.values()) and not changed
                if not report["ok"]:
                    report["reason"] = "files-or-policy-changed"
            return report
    except (OSError, ValueError, UnicodeError) as exc:
        return {"ok": False, "reason": "verification-error", "error": str(exc)}


def audit(project: Path, *, expected_head: str | None = None,
          expected_seq: int | None = None) -> dict:
    outcome = verify(project, check_files=True,
                     expected_head=expected_head, expected_seq=expected_seq)
    scope = None
    if outcome.get("ok") or outcome.get("reason") == "files-or-policy-changed":
        try:
            latest = proof(project)
            scope = {
                "files_included": len(latest["file_hashes"]),
                "policy_version": latest["policy"]["version"],
                "excluded_directories": latest["policy"]["exclude_dirs"],
                "excluded_files": latest["policy"]["exclude_files"],
            }
        except (ValueError, OSError):
            pass
    return {**outcome, "audit_scope": "hash-chain, policy, current files, trusted head",
            "snapshot_scope": scope,
            "warnings": [
                "Ledger setempat boleh diubah oleh sesiapa yang ada akses fail.",
                "Anchoring ke EVM tidak membuktikan pemilikan atau keselamatan kod.",
                "Jangan masukkan rahsia dalam nota anchor.",
                "Data on-chain kekal kelihatan selama-lamanya.",
                "Integrity hashes are not malware checks or digital signatures.",
            ]}


def proof(project: Path, seq: int | None = None) -> dict:
    root = root_path(project)
    with locked(root):
        items = read_entries(root, config_for(root))
        if not items:
            raise ValueError("No snapshots")
        if seq is None:
            seq = len(items) - 1
        if type(seq) is not int or not 0 <= seq < len(items):
            raise ValueError("Invalid snapshot sequence")
        return dict(items[seq])


def backup(project: Path, out: Path) -> dict:
    root = root_path(project)
    dst = Path(out).expanduser().resolve(strict=False)
    if dst == root or dst.is_relative_to(root) or dst.exists():
        raise ValueError("Backup must be a new directory OUTSIDE the project")
    with locked(root):
        cfg = config_for(root)
        items = read_entries(root, cfg)
        if not items:
            raise ValueError("No snapshot to back up")
        dst.mkdir(mode=0o700, parents=False)
        copied = []
        for name in ("config.json", "chain.jsonl", "anchors.jsonl",
                     "legacy-v1-chain.jsonl", "legacy-v1-anchors.jsonl"):
            path = local_path(root, name)
            if not path.exists():
                continue
            raw = read_safe(path)
            create_safe(dst / name, raw)
            copied.append({"file": name, "sha256": hashlib.sha256(raw).hexdigest()})
        checkpoint = {
            "project_id": cfg["project_id"],
            "seq": items[-1]["seq"], "head": items[-1]["entry_hash"],
            "timestamp": utc_now(), "files": copied,
            "warning": "Store this OUTSIDE the project on independently trusted storage.",
        }
        create_safe(dst / "checkpoint.json", canonical(checkpoint) + b"\n")
        return {"status": "exported", "directory": str(dst), **checkpoint}
