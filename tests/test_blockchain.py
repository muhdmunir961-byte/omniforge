"""Blockchain provenance regressions with real local files and JSON-RPC transport."""
from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from omniforge.blockchain import ZERO, anchor_payload, ledger_path, proof, record, snapshot, verify
from omniforge.cli import main
from omniforge.evm import _rpc_url, verify_anchor

WALLET = "0x" + "11" * 20
TXHASH = "0x" + "ab" * 32
BLOCKHASH = "0x" + "cd" * 32


def test_genesis_and_current_snapshot(tmp_path):
    (tmp_path / "app.py").write_text("answer = 1\n")
    result = record(tmp_path, "initial release")
    assert result["height"] == 0
    assert result["previous"] == ZERO
    assert result["files"] == 1
    assert proof(tmp_path) == result
    assert verify(tmp_path, check_current=True)["ok"]
    assert ledger_path(tmp_path).parent.name == ".omniforge"
    assert result["snapshot"] == snapshot(tmp_path)[0]


def test_linked_blocks_and_snapshot_mismatch(tmp_path):
    (tmp_path / "app.py").write_text("x=1")
    first = record(tmp_path)
    (tmp_path / "app.py").write_text("x=2")
    second = record(tmp_path, note="upgrade")
    assert second["height"] == 1
    assert second["previous"] == first["hash"]
    assert second["hash"] != first["hash"]
    assert verify(tmp_path, check_current=True)["ok"]
    (tmp_path / "app.py").write_text("x=3")
    assert verify(tmp_path)["ok"]
    assert not verify(tmp_path, check_current=True)["ok"]


def test_record_fails_on_tampered_entry(tmp_path):
    record(tmp_path)
    p = ledger_path(tmp_path)
    data = p.read_text()
    p.write_text(data.replace('"files":0', '"files":1'))
    report = verify(tmp_path)
    assert not report["ok"] and "Tampered" in report["error"]
    with pytest.raises(ValueError, match="Tampered"):
        record(tmp_path, "must not append")


def test_record_fails_if_last_line_truncated(tmp_path):
    record(tmp_path)
    p = ledger_path(tmp_path)
    p.write_text(p.read_text().rstrip("\n"))
    assert not verify(tmp_path)["ok"]
    with pytest.raises(ValueError, match="incomplete"):
        record(tmp_path)


def test_ledger_rejects_untrusted_symlink(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    chain_dir = tmp_path / ".omniforge"
    try:
        chain_dir.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ValueError, match="symlink"):
        record(tmp_path)
    assert not list(outside.iterdir())


def test_local_hashchain_does_not_claim_decentralization(tmp_path):
    record(tmp_path)
    result = verify(tmp_path)
    assert result["local_only"] is True
    assert "NOT a decentralized" in result["note"]


def test_reject_invalid_note_and_height(tmp_path):
    for note in ["x" * 161, "hello\nworld", "\tbad"]:
        with pytest.raises(ValueError, match="Note"):
            record(tmp_path, note)
    record(tmp_path)
    for height in [-1, 2, True]:
        with pytest.raises(ValueError, match="height"):
            proof(tmp_path, height)


def test_unsigned_evm_self_transaction(tmp_path):
    head = record(tmp_path)
    payload = anchor_payload(tmp_path, address=WALLET, chain_id=1337)
    assert payload["height"] == 0
    assert payload["status"] == "wallet-signature-required"
    assert payload["unsigned_transaction"] == {
        "from": WALLET, "to": WALLET, "value": "0x0",
        "data": "0x" + head["hash"], "chainId": "0x539",
    }
    assert "private_key" not in json.dumps(payload)


def test_reject_invalid_wallet_and_chainid(tmp_path):
    record(tmp_path)
    for address in ["0x123", "0x"+"00"*20, "0x"+"gg"*20]:
        with pytest.raises(ValueError, match="address"):
            anchor_payload(tmp_path, address=address, chain_id=1337)
    for chainid in [0, -1, True, 2**53]:
        with pytest.raises(ValueError, match="chain_id"):
            anchor_payload(tmp_path, address=WALLET, chain_id=chainid)


def test_cli_chain_record_verify_proof_and_anchor(tmp_path, capsys):
    assert main(["blockchain", "record", "--project", str(tmp_path), "--note", "first"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["height"] == 0
    assert main(["blockchain", "verify", "--project", str(tmp_path), "--check-current"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert main(["blockchain", "proof", "--project", str(tmp_path), "--height", "0"]) == 0
    assert json.loads(capsys.readouterr().out)["hash"] == first["hash"]
    assert main(["blockchain", "anchor", "--project", str(tmp_path),
                 "--wallet", WALLET, "--chain-id", "1337"]) == 0
    assert json.loads(capsys.readouterr().out)["ledger_hash"] == first["hash"]
    (tmp_path/"main.py").write_text("new file")
    assert main(["blockchain", "verify", "--project", str(tmp_path), "--check-current"]) == 1


def test_concurrent_writers_are_serialized(tmp_path):
    (tmp_path/"data.txt").write_text("hello")
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda i: record(tmp_path, note=f"entry {i}"), range(12)))
    assert len({x["hash"] for x in results}) == 12
    assert verify(tmp_path)["entries"] == 12
    assert sorted(x["height"] for x in results) == list(range(12))


class RpcHandler(BaseHTTPRequestHandler):
    state = {}

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(size))
        method = payload["method"]
        state = self.__class__.state
        if method == "eth_chainId":
            result = state.get("chain", "0x539")
        elif method == "eth_getTransactionByHash":
            result = state.get("tx")
        elif method == "eth_getTransactionReceipt":
            result = state.get("receipt")
        elif method == "eth_blockNumber":
            result = state.get("height", "0x12")
        else:
            self.send_error(400)
            return
        raw = json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


@pytest.fixture
def rpc_server(tmp_path):
    block = record(tmp_path)
    RpcHandler.state = {
        "tx": {"hash": TXHASH, "input": "0x"+block["hash"],
               "from": WALLET, "to": WALLET, "blockHash": BLOCKHASH},
        "receipt": {"transactionHash": TXHASH, "blockHash": BLOCKHASH,
                    "blockNumber": "0x10", "status": "0x1"},
        "height": "0x12",
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), RpcHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_rpc_verify_confirmed_anchor(tmp_path, rpc_server):
    result = verify_anchor(tmp_path, endpoint=rpc_server,
                           tx_hash=TXHASH, address=WALLET, chain_id=1337,
                           min_confirmations=3)
    assert result["ok"]
    assert result["confirmations"] == 3
    assert result["reason"] == "confirmed"


def test_rpc_insufficient_confirmations(tmp_path, rpc_server):
    result = verify_anchor(tmp_path, endpoint=rpc_server,
                           tx_hash=TXHASH, address=WALLET, chain_id=1337,
                           min_confirmations=4)
    assert not result["ok"]
    assert result["reason"] == "insufficient-confirmations"


def test_rpc_wrong_network_and_wrong_input(tmp_path, rpc_server):
    result = verify_anchor(tmp_path, endpoint=rpc_server,
                           tx_hash=TXHASH, address=WALLET, chain_id=1)
    assert not result["ok"] and result["reason"] == "network-chain-id-mismatch"
    RpcHandler.state["tx"] = {**RpcHandler.state["tx"], "input": "0x"+"ff"*32}
    result = verify_anchor(tmp_path, endpoint=rpc_server,
                           tx_hash=TXHASH, address=WALLET, chain_id=1337)
    assert not result["ok"] and result["reason"] == "transaction-does-not-match-ledger"


def test_rpc_reverted_and_pending(tmp_path, rpc_server):
    RpcHandler.state["receipt"]["status"] = "0x0"
    result = verify_anchor(tmp_path, endpoint=rpc_server,
                           tx_hash=TXHASH, address=WALLET, chain_id=1337)
    assert not result["ok"] and result["reason"] == "transaction-reverted"
    RpcHandler.state["receipt"] = None
    result = verify_anchor(tmp_path, endpoint=rpc_server,
                           tx_hash=TXHASH, address=WALLET, chain_id=1337)
    assert not result["ok"] and result["reason"] == "transaction-not-confirmed"


def test_rpc_rejects_plain_http_remote():
    for endpoint in [
        "http://example.org/rpc", "file:///tmp/rpc",
        "https://user:pass@example.org", "https://example.org/rpc#secret",
    ]:
        with pytest.raises(ValueError):
            _rpc_url(endpoint)
    _rpc_url("https://example.org")
    _rpc_url("http://localhost:8545")


def test_cli_rpc_verify_exit_codes(tmp_path, rpc_server, capsys):
    argv = ["blockchain", "verify-anchor", "--project", str(tmp_path),
            "--wallet", WALLET, "--chain-id", "1337",
            "--tx-hash", TXHASH, "--rpc-url", rpc_server]
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert main(argv + ["--min-confirmations", "4"]) == 1
    assert not json.loads(capsys.readouterr().out)["ok"]


def test_mcp_blockchain_tools_are_read_only(tmp_path):
    from omniforge.mcp import dispatch
    recorded = record(tmp_path)
    file_before = ledger_path(tmp_path).read_bytes()
    listing = dispatch({"jsonrpc":"2.0", "id":1, "method":"tools/list"})["result"]["tools"]
    names = {x["name"] for x in listing}
    assert {"omniforge_chain_verify", "omniforge_chain_proof"} <= names
    for tool in listing:
        if tool["name"] in {"omniforge_chain_verify", "omniforge_chain_proof"}:
            assert "approve" not in tool["inputSchema"]["properties"]

    verification = dispatch({"jsonrpc":"2.0","id":2,"method":"tools/call",
                            "params":{"name":"omniforge_chain_verify",
                                      "arguments":{"project":str(tmp_path),"check_current":True}}})
    report = json.loads(verification["result"]["content"][0]["text"])
    assert report["ok"] and report["head"] == recorded["hash"]
    proof_result = dispatch({"jsonrpc":"2.0","id":3,"method":"tools/call",
                             "params":{"name":"omniforge_chain_proof",
                                       "arguments":{"project":str(tmp_path),"height":0}}})
    block = json.loads(proof_result["result"]["content"][0]["text"])
    assert block["hash"] == recorded["hash"]
    assert ledger_path(tmp_path).read_bytes() == file_before

    bad = dispatch({"jsonrpc":"2.0","id":4,"method":"tools/call",
                    "params":{"name":"omniforge_chain_verify",
                              "arguments":{"project":str(tmp_path),"check_current":"yes"}}})
    assert bad["result"]["isError"]
