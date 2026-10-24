"""Read-only Ethereum JSON-RPC verification for externally signed anchor txs.

OmniForge never stores wallet private keys and never sends transactions.
RPC responses are trusted-provider claims, not independently verified headers.
"""
from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .blockchain import ADDRESS, proof

TXID = re.compile(r"0x[0-9a-fA-F]{64}\Z")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("RPC redirects are not permitted")


def _rpc_url(endpoint: str) -> None:
    if not isinstance(endpoint, str) or len(endpoint) > 2048:
        raise ValueError("Invalid RPC URL")
    parsed = urlsplit(endpoint)
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("RPC URL must not contain credentials or fragments")
    if parsed.scheme == "http":
        if parsed.hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Non-local RPC must use HTTPS")
    elif parsed.scheme != "https":
        raise ValueError("Only HTTPS and loopback HTTP RPC are supported")


def rpc(endpoint: str, method: str, params: list, *, timeout: float = 10) -> object:
    _rpc_url(endpoint)
    if not 0 < timeout <= 30:
        raise ValueError("Invalid RPC timeout")
    if method not in {
        "eth_chainId", "eth_getTransactionByHash", "eth_getTransactionReceipt",
        "eth_blockNumber",
    }:
        raise ValueError("Unsupported read-only RPC method")
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req = Request(endpoint, payload, {
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "OmniForge-provenance/1.2",
    }, method="POST")
    try:
        with build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            data = response.read(128_001)
    except (HTTPError, URLError, OSError) as exc:
        raise ValueError("RPC request failed") from exc
    if len(data) > 128_000:
        raise ValueError("RPC response too large")
    try:
        obj = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid RPC JSON response") from exc
    if not isinstance(obj, dict) or obj.get("jsonrpc") != "2.0" or obj.get("id") != 1:
        raise ValueError("Malformed JSON-RPC response")
    if "error" in obj:
        raise ValueError("RPC provider returned an error")
    if "result" not in obj:
        raise ValueError("Missing RPC result")
    return obj["result"]


def _quantity(value: object) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        raise ValueError("Malformed blockchain numeric quantity")
    return int(value, 16)


def verify_anchor(project, *, endpoint: str, tx_hash: str, address: str,
                  chain_id: int, height: int | None = None,
                  min_confirmations: int = 1) -> dict:
    """Verify that a confirmed self-tx has exactly the selected ledger SHA-256."""
    if not isinstance(tx_hash, str) or not TXID.fullmatch(tx_hash):
        raise ValueError("Invalid transaction hash")
    if not isinstance(address, str) or not ADDRESS.fullmatch(address) or int(address[2:], 16) == 0:
        raise ValueError("Invalid expected wallet address")
    if type(chain_id) is not int or not 1 <= chain_id < 2**53:
        raise ValueError("Invalid expected chain ID")
    if type(min_confirmations) is not int or not 1 <= min_confirmations <= 100_000:
        raise ValueError("min_confirmations must be between 1 and 100000")
    block = proof(project, height)
    network = _quantity(rpc(endpoint, "eth_chainId", []))
    if network != chain_id:
        return {"ok": False, "reason": "network-chain-id-mismatch",
                "expected_chain_id": chain_id, "rpc_chain_id": network}
    tx = rpc(endpoint, "eth_getTransactionByHash", [tx_hash])
    receipt = rpc(endpoint, "eth_getTransactionReceipt", [tx_hash])
    if not isinstance(tx, dict) or receipt is None:
        return {"ok": False, "reason": "transaction-not-confirmed"}
    if not isinstance(receipt, dict):
        raise ValueError("Malformed transaction receipt")
    expected_input = "0x" + block["hash"]
    fields_match = all([
        str(tx.get("hash", "")).lower() == tx_hash.lower(),
        str(tx.get("input", "")).lower() == expected_input.lower(),
        str(tx.get("to", "")).lower() == address.lower(),
        str(tx.get("from", "")).lower() == address.lower(),
        str(receipt.get("transactionHash", "")).lower() == tx_hash.lower(),
        str(receipt.get("blockHash", "")).lower() == str(tx.get("blockHash", "")).lower(),
    ])
    if not fields_match:
        return {"ok": False, "reason": "transaction-does-not-match-ledger"}
    if _quantity(receipt.get("status")) != 1:
        return {"ok": False, "reason": "transaction-reverted"}
    mined_at = _quantity(receipt.get("blockNumber"))
    latest = _quantity(rpc(endpoint, "eth_blockNumber", []))
    if latest < mined_at:
        raise ValueError("RPC block height is inconsistent")
    confirmations = latest - mined_at + 1
    return {
        "ok": confirmations >= min_confirmations,
        "reason": "confirmed" if confirmations >= min_confirmations else "insufficient-confirmations",
        "chain_id": network, "ledger_height": block["height"], "ledger_hash": block["hash"],
        "tx_hash": tx_hash, "confirmations": confirmations,
        "rpc_trust_note": "Verified against the chosen RPC provider, not an independently validated consensus node.",
    }
