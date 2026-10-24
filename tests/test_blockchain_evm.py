"""Actual EVM integration on a disposable Ganache chain, never on mainnet.

A local unlocked test account sends a zero-value self-transaction containing
OmniForge's 32-byte SHA-256 ledger hash as calldata. This spends only simulated
Ganache currency. No user keys or external RPC providers are used.
"""
from __future__ import annotations

import json
import os
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


def test_real_ethereum_compatible_anchor(tmp_path: Path):
    assert int(send_rpc("eth_chainId", []), 16) == 1337
    accounts = send_rpc("eth_accounts", [])
    assert accounts
    address = accounts[0]
    (tmp_path / "skill.py").write_text("value = 1\n", encoding="utf-8")
    first = record(tmp_path, "local Ganache attestation")
    prepared = anchor_payload(tmp_path, address=address, chain_id=1337)
    assert prepared["ledger_hash"] == first["hash"]
    tx = prepared["unsigned_transaction"]
    assert tx["from"].lower() == tx["to"].lower() == address.lower()
    assert tx["value"] == "0x0"
    assert tx["data"] == "0x" + first["hash"]

    # Ganache test accounts are deliberately unlocked; OmniForge never has
    # wallet private keys or a live transaction-submission command.
    txid = send_rpc("eth_sendTransaction", [{
        "from": address, "to": address, "value": "0x0",
        "data": tx["data"], "gas": "0x186a0",
    }])
    receipt = send_rpc("eth_getTransactionReceipt", [txid])
    assert receipt is not None and receipt["status"] == "0x1"

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
