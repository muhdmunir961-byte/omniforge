"""EVM anchoring for OF-Provenance v2: unsigned payloads, read-only verification.

No wallet private keys, signing, transaction submission or monetary operations.
Only explicit user-approved external wallets can ever send the prepared payload.
"""
from __future__ import annotations
from pathlib import Path
from .evm import ADDRESS, TXID, _quantity, rpc
from .provenance_v2 import proof, verify


def _wallet(value: object) -> str:
    if not isinstance(value, str) or not ADDRESS.fullmatch(value) or not int(value[2:], 16):
        raise ValueError("Provide a nonzero public 0x-prefixed EVM wallet address")
    return value


def _chain(value: object) -> int:
    if type(value) is not int or not 1 <= value < 2**53:
        raise ValueError("chain_id must be a positive integer")
    return value


def prepare(project: Path, *, seq: int | None, wallet: str, chain_id: int,
            ack_public_data: bool = False) -> dict:
    if ack_public_data is not True:
        raise ValueError("Explicit --ack-public-data required to prepare public calldata")
    _wallet(wallet)
    _chain(chain_id)
    status = verify(project)
    if not status["ok"]:
        raise ValueError("Cannot anchor a broken/empty ledger")
    item = proof(project, seq)
    return {
        "status": "wallet-approval-required",
        "seq": item["seq"], "entry_hash": item["entry_hash"],
        "unsigned_transaction": {
            "from": wallet, "to": wallet, "value": "0x0",
            "data": "0x" + item["entry_hash"], "chainId": hex(chain_id),
        },
        "warning": ("NO transaction was sent or signed. Your wallet will require "
                    "explicit approval and may charge gas. Public on-chain data is permanent."),
    }


def check_tx(project: Path, *, seq: int | None, wallet: str, chain_id: int,
             tx_hash: str, endpoint: str, min_confirmations: int = 1) -> dict:
    _wallet(wallet)
    _chain(chain_id)
    if not isinstance(tx_hash, str) or not TXID.fullmatch(tx_hash):
        raise ValueError("Invalid EVM transaction hash")
    if type(min_confirmations) is not int or not 1 <= min_confirmations <= 100_000:
        raise ValueError("Confirmations must be 1..100000")
    status = verify(project)
    if not status["ok"]:
        raise ValueError("Ledger verification must pass before RPC verification")
    item = proof(project, seq)
    network = _quantity(rpc(endpoint, "eth_chainId", []))
    if network != chain_id:
        return {"ok": False, "reason": "chain-id-mismatch"}
    transaction = rpc(endpoint, "eth_getTransactionByHash", [tx_hash])
    receipt = rpc(endpoint, "eth_getTransactionReceipt", [tx_hash])
    if not isinstance(transaction, dict) or receipt is None:
        return {"ok": False, "reason": "transaction-unconfirmed"}
    if not isinstance(receipt, dict):
        raise ValueError("Invalid RPC receipt shape")
    expected = "0x" + item["entry_hash"]
    same = all((
        str(transaction.get("hash", "")).lower() == tx_hash.lower(),
        str(transaction.get("from", "")).lower() == wallet.lower(),
        str(transaction.get("to", "")).lower() == wallet.lower(),
        str(transaction.get("input", "")).lower() == expected.lower(),
        str(receipt.get("transactionHash", "")).lower() == tx_hash.lower(),
        bool(transaction.get("blockHash")),
        str(transaction.get("blockHash", "")).lower() == str(receipt.get("blockHash", "")).lower(),
        str(transaction.get("blockNumber", "")).lower() == str(receipt.get("blockNumber", "")).lower(),
    ))
    if not same:
        return {"ok": False, "reason": "transaction-content-mismatch"}
    if _quantity(transaction.get("value")) != 0:
        return {"ok": False, "reason": "nonzero-value"}
    if _quantity(receipt.get("status")) != 1:
        return {"ok": False, "reason": "transaction-reverted"}
    mined = _quantity(receipt.get("blockNumber"))
    latest = _quantity(rpc(endpoint, "eth_blockNumber", []))
    if latest < mined:
        raise ValueError("RPC reported a block earlier than the receipt")
    confirmations = latest - mined + 1
    return {
        "ok": confirmations >= min_confirmations,
        "reason": "confirmed" if confirmations >= min_confirmations else "insufficient-confirmations",
        "chain_id": chain_id, "seq": item["seq"],
        "entry_hash": item["entry_hash"], "tx_hash": tx_hash,
        "confirmations": confirmations,
        "trust_boundary": ("Read-only JSON-RPC provider response, not independent "
                           "Ethereum consensus verification or author identity."),
    }
