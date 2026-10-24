"""Actual EVM integration on a disposable Anvil chain, never on mainnet.

A local unlocked test account sends a zero-value self-transaction containing
OmniForge's 32-byte SHA-256 ledger hash as calldata. This spends only simulated
Anvil currency. No user keys or external RPC providers are used.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from omniforge.blockchain import anchor_payload, record
from omniforge.evm import verify_anchor

pytestmark = pytest.mark.skipif(
    os.environ.get("OMNIFORGE_CHAIN_LIVE") != "1",
    reason="requires disposable local EVM node; run via GitHub E2E blockchain job",
)

ENDPOINT = "http://127.0.0.1:8545"


def send_rpc(method: str, params: list) -> object:
    request = Request(
        ENDPOINT,
        json.dumps({"jsonrpc": "2.0", "id": 99, "method": method, "params": params}).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as result:
        response = json.load(result)
    if "error" in response:
        raise AssertionError(f"Local EVM RPC error for {method}: {response['error']}")
    return response["result"]


def await_receipt(txid: str) -> dict:
    """Anvil may mine asynchronously; never assume receipt is instant."""
    for attempt in range(60):
        receipt = send_rpc("eth_getTransactionReceipt", [txid])
        if receipt is not None:
            return receipt
        time.sleep(0.1)
    raise AssertionError("Local Anvil did not mine the test transaction within 6 seconds")


def test_real_ethereum_compatible_anchor(tmp_path: Path):
    assert int(send_rpc("eth_chainId", []), 16) == 1337
    accounts = send_rpc("eth_accounts", [])
    assert accounts
    address = accounts[0]
    (tmp_path / "skill.py").write_text("value = 1\n", encoding="utf-8")
    first = record(tmp_path, "local Anvil attestation")
    prepared = anchor_payload(tmp_path, address=address, chain_id=1337)
    assert prepared["ledger_hash"] == first["hash"]
    tx = prepared["unsigned_transaction"]
    assert tx["from"].lower() == tx["to"].lower() == address.lower()
    assert tx["value"] == "0x0"
    assert tx["data"] == "0x" + first["hash"]

    # Anvil test accounts are deliberately unlocked; OmniForge never has
    # wallet private keys or a live transaction-submission command.
    txid = send_rpc("eth_sendTransaction", [{
        "from": address, "to": address, "value": "0x0",
        "data": tx["data"], "gas": "0x186a0",
    }])
    receipt = await_receipt(txid)
    assert receipt["status"] == "0x1"

    valid = verify_anchor(
        tmp_path, endpoint=ENDPOINT, tx_hash=txid, address=address,
        chain_id=1337, height=0,
    )
    assert valid["ok"], valid
    assert valid["ledger_hash"] == first["hash"]
    assert valid["confirmations"] >= 1

    # Different ledger record must not be accepted for the old transaction.
    (tmp_path / "skill.py").write_text("value = 2\n", encoding="utf-8")
    record(tmp_path, "new code snapshot")
    wrong = verify_anchor(
        tmp_path, endpoint=ENDPOINT, tx_hash=txid, address=address,
        chain_id=1337, height=1,
    )
    assert not wrong["ok"] and wrong["reason"] == "transaction-does-not-match-ledger"
    original = verify_anchor(
        tmp_path, endpoint=ENDPOINT, tx_hash=txid, address=address,
        chain_id=1337, height=0,
    )
    assert original["ok"]


def test_real_v2_provenance_anchor_and_rpc_verification(tmp_path: Path):
    """Sign/broadcast ONLY with an unlocked disposable Anvil testing account."""
    from omniforge import provenance_v2 as v2
    from omniforge.provenance_v2_evm import prepare as v2_prepare, check_tx

    accounts = send_rpc("eth_accounts", [])
    assert accounts and int(send_rpc("eth_chainId", []), 16) == 1337
    wallet = accounts[0]
    (tmp_path / "new-feature.py").write_text("integrity = True\n")
    v2.init(tmp_path)
    entry = v2.snapshot(tmp_path, note="new v2 source")
    prepared = v2_prepare(tmp_path, seq=0, wallet=wallet, chain_id=1337,
                          ack_public_data=True)
    transaction = prepared["unsigned_transaction"]
    assert transaction["data"] == "0x" + entry["entry_hash"]
    assert transaction["value"] == "0x0"
    # The application never sends transactions. This test harness alone
    # broadcasts using disposable test accounts in the local Anvil node.
    txid = send_rpc("eth_sendTransaction", [{
        "from": wallet, "to": wallet, "value": "0x0", "data": transaction["data"],
        "gas": "0x186a0",
    }])
    assert await_receipt(txid)["status"] == "0x1"
    verified = check_tx(tmp_path, seq=0, wallet=wallet, chain_id=1337,
                        tx_hash=txid, endpoint=ENDPOINT)
    assert verified["ok"], verified
    assert verified["entry_hash"] == entry["entry_hash"]
    assert verified["confirmations"] >= 1
    saved = v2.save_rpc_receipt(tmp_path, verified, wallet=wallet)
    assert saved["status"] == "journaled-local-only"
    assert v2.verify(tmp_path)["anchor_evidence_events"] == 1
    assert v2.proof(tmp_path, 0)["anchor_status"] == "not_requested"

    (tmp_path / "new-feature.py").write_text("integrity = False\n")
    v2.snapshot(tmp_path)
    mismatch = check_tx(tmp_path, seq=1, wallet=wallet, chain_id=1337,
                        tx_hash=txid, endpoint=ENDPOINT)
    assert not mismatch["ok"] and mismatch["reason"] == "transaction-content-mismatch"
