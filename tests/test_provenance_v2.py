"""OF-Provenance v2 security and compatibility tests (no wallet/network needed)."""
from __future__ import annotations
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

from omniforge import provenance_v2 as v2
from omniforge.provenance_v2_policy import (
    DEFAULT_POLICY, canonical, hashed, policy_digest, scan_project, snapshot_digest,
)
from omniforge.provenance_v2_cli import main
from omniforge.provenance_v2_evm import prepare
from omniforge.blockchain import record as legacy_record, verify as legacy_verify

WALLET = "0x" + "11" * 20


def initialize(tmp_path):
    v2.init(tmp_path)
    return v2.snapshot(tmp_path)


def chain_path(tmp_path):
    return tmp_path / ".of-provenance" / "chain.jsonl"


def config_path(tmp_path):
    return tmp_path / ".of-provenance" / "config.json"


def rows(tmp_path):
    return [json.loads(row) for row in chain_path(tmp_path).read_text().splitlines()]


def write_rows(tmp_path, data):
    chain_path(tmp_path).write_text("".join(canonical(x).decode() + "\n" for x in data))


def rebuild_chain(tmp_path, mutate):
    entries = rows(tmp_path)
    mutate(entries)
    prev = "0" * 64
    for idx, item in enumerate(entries):
        item["seq"] = idx
        item["prev_hash"] = prev
        item["entry_hash"] = hashed(b"OF-ENTRY-v2",
                                    {k: v for k, v in item.items() if k != "entry_hash"})
        prev = item["entry_hash"]
    write_rows(tmp_path, entries)


def test_init_then_snapshot_verify_and_file_changes(tmp_path):
    (tmp_path / "app.py").write_text("answer=1\n")
    start = v2.init(tmp_path)
    assert start["version"] == 2
    first = v2.snapshot(tmp_path, note="start")
    assert first["files"] == 1
    assert v2.verify(tmp_path, check_files=True)["ok"]
    (tmp_path / "app.py").write_text("answer=2\n")
    result = v2.verify(tmp_path, check_files=True)
    assert not result["ok"] and result["files"]["modified"] == ["app.py"]
    second = v2.snapshot(tmp_path, note="edited", expected_head=first["entry_hash"])
    assert second["seq"] == 1
    assert v2.verify(tmp_path, check_files=True)["ok"]
    assert rows(tmp_path)[1]["prev_hash"] == first["entry_hash"]
    assert v2.proof(tmp_path, 0)["entry_hash"] == first["entry_hash"]


def test_files_missing_added_and_ignored_secret(tmp_path):
    (tmp_path / "a.py").write_text("1")
    (tmp_path / ".env").write_text("SECRET=NEVER_STORE_ME")
    (tmp_path / ".env.local").write_text("TOKEN=ALSO_SKIP")
    initialize(tmp_path)
    block = v2.proof(tmp_path)
    assert sorted(block["file_hashes"]) == ["a.py"]
    (tmp_path / "a.py").unlink()
    (tmp_path / "new.py").write_text("2")
    difference = v2.audit(tmp_path)
    assert not difference["ok"]
    assert difference["files"]["missing"] == ["a.py"]
    assert difference["files"]["added"] == ["new.py"]
    assert "NEVER_STORE_ME" not in chain_path(tmp_path).read_text()


def test_recomputed_hash_with_unexpected_field_is_rejected(tmp_path):
    initialize(tmp_path)
    rebuild_chain(tmp_path, lambda entries: entries[0].update({"malicious": True}))
    assert not v2.verify(tmp_path)["ok"]


def test_recomputed_hash_with_invalid_relative_path_is_rejected(tmp_path):
    initialize(tmp_path)
    def alter(entries):
        entry = entries[0]
        entry["file_hashes"]["../outside.py"] = "0" * 64
        entry["snapshot_hash"] = snapshot_digest({})  # incorrect deliberately
    rebuild_chain(tmp_path, alter)
    assert not v2.verify(tmp_path)["ok"]


def test_recomputed_hash_with_invalid_policy_is_rejected(tmp_path):
    initialize(tmp_path)
    def alter(entries):
        entry = entries[0]
        entry["policy"]["unknown_setting"] = "enabled"
        entry["policy_hash"] = hashed(b"OF-POLICY-v2", entry["policy"])
    rebuild_chain(tmp_path, alter)
    result = v2.verify(tmp_path)
    assert not result["ok"]


def test_recomputed_hash_wrong_uuid_and_boolean_seq_rejected(tmp_path):
    initialize(tmp_path)
    rebuild_chain(tmp_path, lambda e: e[0].update({"project_id": "not-a-uuid"}))
    assert not v2.verify(tmp_path)["ok"]
    # Restore by re-initializing in a new folder.
    other = tmp_path / "other"
    other.mkdir()
    initialize(other)
    data = rows(other)
    data[0]["seq"] = True
    write_rows(other, data)
    assert not v2.verify(other)["ok"]


def test_duplicate_json_keys_rejected_even_if_hash_was_valid(tmp_path):
    initialize(tmp_path)
    raw = chain_path(tmp_path).read_text()
    chain_path(tmp_path).write_text(raw.replace('"version":2', '"version":2,"version":2'))
    assert not v2.verify(tmp_path)["ok"]


def test_truncated_ledger_rejected_and_no_append(tmp_path):
    initialize(tmp_path)
    path = chain_path(tmp_path)
    old = path.read_text()
    path.write_text(old.rstrip("\n"))
    assert not v2.verify(tmp_path)["ok"]
    with pytest.raises(ValueError, match="incomplete"):
        v2.snapshot(tmp_path)


def test_policy_history_requires_opt_in_to_change(tmp_path):
    (tmp_path / "src.py").write_text("ok")
    initialize(tmp_path)
    config = json.loads(config_path(tmp_path).read_text())
    config["policy"]["exclude_files"].append("src.py")
    config_path(tmp_path).write_text(json.dumps(config))
    status = v2.verify(tmp_path, check_files=True)
    assert status["policy_changed"] and not status["ok"]
    with pytest.raises(ValueError, match="Policy changed"):
        v2.snapshot(tmp_path)
    result = v2.snapshot(tmp_path, allow_policy_change=True)
    assert result["seq"] == 1
    older, newer = rows(tmp_path)
    assert "src.py" in older["file_hashes"]
    assert "src.py" not in newer["file_hashes"]
    assert older["policy_hash"] != newer["policy_hash"]
    assert older["policy_hash"] == policy_digest(older["policy"])
    assert v2.verify(tmp_path, check_files=True)["ok"]


def test_trusted_checkpoint_detects_rewrite_of_entire_chain(tmp_path):
    initialize(tmp_path)
    first = v2.snapshot(tmp_path, note="trusted state")
    head = first["entry_hash"]
    assert v2.verify(tmp_path, expected_head=head, expected_seq=1)["ok"]
    rebuild_chain(tmp_path, lambda entries: entries[1].update({"note": "rewritten history"}))
    assert v2.verify(tmp_path)["ok"]  # a fully rewritten local chain can fool local-only checks
    trusted = v2.verify(tmp_path, expected_head=head, expected_seq=1)
    assert not trusted["ok"] and trusted["reason"] == "trusted-checkpoint-mismatch"


def test_trusted_checkpoint_detects_truncation(tmp_path):
    initialize(tmp_path)
    second = v2.snapshot(tmp_path)
    path = chain_path(tmp_path)
    path.write_text(path.read_text().splitlines()[0] + "\n")
    assert v2.verify(tmp_path)["ok"]  # local-only tip still self-consistent
    assert not v2.verify(tmp_path, expected_head=second["entry_hash"], expected_seq=1)["ok"]


def test_unpaired_or_invalid_checkpoint_rejected(tmp_path):
    initialize(tmp_path)
    with pytest.raises(ValueError, match="Both"):
        v2.verify(tmp_path, expected_head="0"*64)
    with pytest.raises(ValueError, match="Invalid trusted"):
        v2.verify(tmp_path, expected_head="0"*64, expected_seq=True)


def test_duplicate_init_refuses_overwrite(tmp_path):
    initialize(tmp_path)
    original = chain_path(tmp_path).read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        v2.init(tmp_path)
    assert chain_path(tmp_path).read_bytes() == original


def test_legacy_v1_migration_preserves_hashes_and_original_bytes(tmp_path):
    (tmp_path/"main.py").write_text("old=1")
    old_block = legacy_record(tmp_path, "legacy release")
    old_path = tmp_path / ".omniforge" / "chain.jsonl"
    old_bytes = old_path.read_bytes()
    before = v2.migrate(tmp_path)
    assert before["status"] == "preview-only"
    assert not (tmp_path/".of-provenance").exists()
    result = v2.migrate(tmp_path, approve=True)
    assert result["legacy_ref"]["head"] == old_block["hash"]
    assert old_path.read_bytes() == old_bytes
    assert legacy_verify(tmp_path)["ok"]
    backup = tmp_path / ".of-provenance" / "legacy-v1-chain.jsonl"
    assert backup.read_bytes() == old_bytes
    genesis = v2.snapshot(tmp_path)
    assert genesis["seq"] == 0
    assert v2.proof(tmp_path, 0)["legacy_ref"]["head"] == old_block["hash"]
    assert v2.verify(tmp_path, check_files=True)["ok"]
    assert backup.read_bytes() == old_bytes


def test_legacy_backup_mutation_detected(tmp_path):
    legacy_record(tmp_path)
    v2.migrate(tmp_path, approve=True)
    v2.snapshot(tmp_path)
    (tmp_path / ".of-provenance" / "legacy-v1-chain.jsonl").write_bytes(b"evil\n")
    assert not v2.verify(tmp_path)["ok"]


def test_old_api_works_when_no_v2_migration_requested(tmp_path):
    legacy_record(tmp_path)
    with pytest.raises(ValueError, match="migrate"):
        v2.init(tmp_path)
    assert legacy_verify(tmp_path)["ok"]


def test_concurrent_writes_use_ledger_lock(tmp_path):
    initialize(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda n: v2.snapshot(tmp_path, note=str(n)), range(8)))
    assert sorted(x["seq"] for x in results) == list(range(1, 9))
    assert v2.verify(tmp_path)["entries"] == 9


def test_excess_file_count_fails_closed(tmp_path):
    v2.init(tmp_path)
    config = json.loads(config_path(tmp_path).read_text())
    config["policy"]["max_files"] = 1
    config_path(tmp_path).write_text(json.dumps(config))
    (tmp_path/"a.txt").write_text("a")
    (tmp_path/"b.txt").write_text("b")
    with pytest.raises(ValueError, match="max_files"):
        v2.snapshot(tmp_path)


def test_special_files_and_symlinks_refused(tmp_path):
    v2.init(tmp_path)
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.write_text("outside")
    try:
        (tmp_path/"escape.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="Symlinked"):
        v2.snapshot(tmp_path)


def test_backup_outside_project_and_reject_internal(tmp_path):
    initialize(tmp_path)
    with pytest.raises(ValueError, match="OUTSIDE"):
        v2.backup(tmp_path, tmp_path/"internal")
    destination = tmp_path.parent / (tmp_path.name + "-secure-backup")
    result = v2.backup(tmp_path, destination)
    assert (destination/"checkpoint.json").is_file()
    assert result["head"] == v2.proof(tmp_path)["entry_hash"]
    assert result["files"]


def test_unsafe_anchor_without_ack_refused(tmp_path):
    initialize(tmp_path)
    with pytest.raises(ValueError, match="ack-public-data"):
        prepare(tmp_path, seq=0, wallet=WALLET, chain_id=1337)
    unsigned = prepare(tmp_path, seq=0, wallet=WALLET, chain_id=1337,
                       ack_public_data=True)
    assert unsigned["unsigned_transaction"]["data"] == "0x"+v2.proof(tmp_path)["entry_hash"]
    assert unsigned["unsigned_transaction"]["value"] == "0x0"
    assert unsigned["status"] == "wallet-approval-required"
    assert "private_key" not in json.dumps(unsigned)


def test_cli_round_trip_and_nonzero_on_integrity_error(tmp_path, capsys):
    assert main(["init", "--project", str(tmp_path)]) == 0
    capsys.readouterr()
    (tmp_path/"a.py").write_text("x=1")
    assert main(["snapshot", "--project", str(tmp_path)]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert main(["verify", "--project", str(tmp_path), "--check-files",
                 "--expected-head", entry["entry_hash"], "--expected-seq", "0"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    (tmp_path/"a.py").unlink()
    assert main(["audit", "--project", str(tmp_path)]) == 1
    assert "missing" in capsys.readouterr().out


def test_entry_hash_has_domain_separator(tmp_path):
    initialize(tmp_path)
    entry = v2.proof(tmp_path)
    payload = {k: v for k, v in entry.items() if k != "entry_hash"}
    assert entry["entry_hash"] == hashed(b"OF-ENTRY-v2", payload)
    assert entry["snapshot_hash"] == snapshot_digest(entry["file_hashes"])
