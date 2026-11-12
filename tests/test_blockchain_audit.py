"""Cross-cutting blockchain audit: v1 + v2 coexistence and documented semantics.

The per-module suites cover each ledger in isolation. These tests pin the
*contracts between* them and the semantics that are easy to misread:

* v2 must never modify or invalidate the legacy v1 ledger, and both may live in
  the same project at the same time.
* ``verify()`` without ``check_files`` reports chain integrity only; it cannot
  detect an edited source file. That is by design, and it is the trap that makes
  a tampered project look healthy.
"""
from __future__ import annotations

import json

import pytest

from omniforge import provenance_v2 as v2
from omniforge.blockchain import anchor_payload
from omniforge.blockchain import proof as chain_proof
from omniforge.blockchain import record as chain_record
from omniforge.blockchain import verify as chain_verify
from omniforge.mcp import dispatch

WALLET = "0x" + "11" * 20


def _chain_lines(project) -> list[dict]:
    path = project / ".omniforge" / "chain.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _call_tool(name: str, **arguments) -> dict:
    response = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": name, "arguments": arguments}})
    return json.loads(response["result"]["content"][0]["text"])


def test_v1_and_v2_ledgers_coexist_after_migration(tmp_path):
    """After an explicit copy-only migration, both ledgers record independently.

    ``v2.init`` deliberately refuses when a v1 ledger exists (see the next test),
    so coexistence is only reachable through ``migrate --approve``, which copies
    the v1 bytes without rewriting them.
    """
    (tmp_path / "app.py").write_text("answer = 1\n")

    first = chain_record(tmp_path, "v1 genesis")
    assert first["height"] == 0
    migrated = v2.migrate(tmp_path, approve=True)
    assert migrated["status"] == "migrated"
    snap = v2.snapshot(tmp_path, note="v2 genesis")

    # A second v1 record after v2 exists must still append to the v1 chain.
    second = chain_record(tmp_path, "v1 after v2")
    assert second["height"] == 1
    assert second["previous"] == first["hash"]

    # v2 must remain valid and unchanged by the later v1 write.
    assert v2.verify(tmp_path, check_files=True)["ok"]
    assert v2.proof(tmp_path, 0)["entry_hash"] == snap["entry_hash"]
    assert chain_verify(tmp_path, check_current=True)["ok"]

    # Both ledgers are separate files and separate directories.
    assert (tmp_path / ".omniforge" / "chain.jsonl").is_file()
    assert (tmp_path / ".of-provenance" / "chain.jsonl").is_file()


def test_v1_snapshot_ignores_v2_state_directory(tmp_path):
    """The v1 manifest must not absorb .of-provenance, or v1 verify would break."""
    (tmp_path / "app.py").write_text("answer = 1\n")
    chain_record(tmp_path, "before v2")
    before = chain_verify(tmp_path, check_current=True)
    assert before["ok"]

    v2.migrate(tmp_path, approve=True)
    v2.snapshot(tmp_path)

    after = chain_verify(tmp_path, check_current=True)
    assert after["ok"], "v2 state must not change the v1 snapshot"


def test_v2_init_refuses_when_only_v1_exists(tmp_path):
    """Silent conversion would destroy v1 evidence, so it must be refused."""
    (tmp_path / "app.py").write_text("answer = 1\n")
    chain_record(tmp_path, "legacy")
    with pytest.raises(ValueError, match="migrate"):
        v2.init(tmp_path)
    # The v1 ledger is still intact and verifiable.
    assert chain_verify(tmp_path, check_current=True)["ok"]


def test_verify_without_check_files_cannot_see_an_edited_file(tmp_path):
    """Chain integrity and file integrity are separate, documented concerns.

    ``verify()`` defaults to chain-only. A caller that forgets ``check_files``
    gets ``ok: True`` for an edited project, so the difference must stay
    explicit and tested.
    """
    (tmp_path / "app.py").write_text("answer = 1\n")
    v2.init(tmp_path)
    v2.snapshot(tmp_path)
    (tmp_path / "app.py").write_text("answer = 666\n")

    chain_only = v2.verify(tmp_path)
    assert chain_only["ok"] is True
    assert "files" not in chain_only, "chain-only verify must not report file state"

    with_files = v2.verify(tmp_path, check_files=True)
    assert with_files["ok"] is False
    assert with_files["files"]["modified"] == ["app.py"]
    assert with_files["reason"] == "files-or-policy-changed"


def test_mcp_provenance_verify_defaults_to_chain_only(tmp_path):
    """The MCP tool mirrors the Python default; check_files must be requested."""
    (tmp_path / "app.py").write_text("answer = 1\n")
    v2.init(tmp_path)
    v2.snapshot(tmp_path)
    (tmp_path / "app.py").write_text("answer = 666\n")

    assert _call_tool("omniforge_provenance_verify", project=str(tmp_path))["ok"] is True
    strict = _call_tool("omniforge_provenance_verify",
                        project=str(tmp_path), check_files=True)
    assert strict["ok"] is False
    assert strict["files"]["modified"] == ["app.py"]


def test_audit_is_strict_where_verify_is_lax(tmp_path):
    """audit() always hashes files, so it catches what plain verify() misses."""
    (tmp_path / "app.py").write_text("answer = 1\n")
    v2.init(tmp_path)
    v2.snapshot(tmp_path)
    (tmp_path / "app.py").write_text("answer = 666\n")

    assert v2.verify(tmp_path)["ok"] is True
    audit = v2.audit(tmp_path)
    assert audit["ok"] is False
    assert audit["files"]["modified"] == ["app.py"]
    assert audit["snapshot_scope"]["files_included"] == 1


def test_both_ledgers_detect_their_own_tampering_independently(tmp_path):
    """Tampering one ledger must not mask the other."""
    (tmp_path / "app.py").write_text("answer = 1\n")
    chain_record(tmp_path, "v1")
    v2.migrate(tmp_path, approve=True)
    v2.snapshot(tmp_path)

    # Corrupt only the v1 record.
    v1_path = tmp_path / ".omniforge" / "chain.jsonl"
    original = v1_path.read_bytes()
    rows = _chain_lines(tmp_path)
    rows[0]["note"] = "rewritten"
    v1_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    assert chain_verify(tmp_path)["ok"] is False
    assert v2.verify(tmp_path, check_files=True)["ok"] is True

    # Restore v1 from the bytes captured before tampering, then corrupt only v2.
    v1_path.write_bytes(original)
    chain_record(tmp_path, "v1 repaired")
    assert chain_verify(tmp_path)["ok"] is True

    v2_path = tmp_path / ".of-provenance" / "chain.jsonl"
    raw = v2_path.read_text(encoding="utf-8")
    v2_path.write_text(raw.replace('"seq":0', '"seq":1', 1), encoding="utf-8")
    assert v2.verify(tmp_path)["ok"] is False
    assert chain_verify(tmp_path)["ok"] is True


def test_v1_anchor_uses_recorded_hash_and_stays_unsigned(tmp_path):
    (tmp_path / "app.py").write_text("answer = 1\n")
    block = chain_record(tmp_path, "anchor me")
    payload = anchor_payload(tmp_path, address=WALLET, chain_id=1337)
    assert payload["status"] == "wallet-signature-required"
    assert payload["ledger_hash"] == block["hash"]
    assert payload["unsigned_transaction"]["data"] == "0x" + block["hash"]
    assert payload["unsigned_transaction"]["value"] == "0x0"
    assert payload["unsigned_transaction"]["to"] == WALLET
    # No signing material is ever produced or requested.
    assert "private" not in json.dumps(payload).lower()


def test_chain_proof_returns_exact_stored_block(tmp_path):
    (tmp_path / "app.py").write_text("answer = 1\n")
    block = chain_record(tmp_path, "exact")
    assert chain_proof(tmp_path, 0) == block
    with pytest.raises(ValueError):
        chain_proof(tmp_path, 1)
    with pytest.raises(ValueError):
        chain_proof(tmp_path, -1)
