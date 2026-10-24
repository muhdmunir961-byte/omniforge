# Blockchain provenance for OmniForge

OmniForge includes an **opt-in provenance ledger**, with an optional Ethereum-compatible *transaction anchor*. This feature is for verifying a snapshot of your project or skill source. It is **not** a new cryptocurrency, smart-contract platform, token, mining system, proof-of-stake chain, or decentralized consensus network.

## Architecture

```text
Project files (excluding .git, .omniforge and build cache)
      |
      v
SHA-256 manifest snapshot
      |
      v
Local chain.jsonl: height, timestamp, snapshot digest, previous hash
      |
      v
New SHA-256 block hash = SHA-256(canonical record)
      |
      v
Optional unsigned EVM self-transfer (value=0, data=0x<block hash>)
      |
      v
User wallet signs + broadcasts / pays network gas
      |
      v
Read-only JSON-RPC verification of confirmed transaction
```

**Default:** offline, local-only, zero wallet setup, zero transaction fees.

## Quickstart (no blockchain account required)

From the project you want to attest:

```bash
omniforge blockchain record --project . --note "release build"
omniforge blockchain verify --project . --check-current
omniforge blockchain proof --project . --height 0
```

Records are stored in `.omniforge/chain.jsonl` within the project, a path excluded from OmniForge's manifest snapshot. Each block stores only the snapshot digest, file count, note, UTC timestamp, previous block hash and its own SHA-256 digest. **No file contents or private keys are stored on the ledger.** Use harmless short notes; notes and metadata might still reveal information.

The ledger serializes concurrent writes with a filesystem lock. If an old record is edited or truncated, verification fails and new records are refused. `verify --check-current` also confirms that the newest recorded snapshot matches the current project contents. Earlier snapshots are not reconstructible from hashes alone.

**Important security boundary:** a local mutable hash-chain is only tamper-evident against unsophisticated edits. Someone with filesystem write access can rewrite the entire local history, including every computed hash. Protect/export the ledger head externally or anchor it on a real blockchain to establish a stronger comparison point. This ledger by itself has no consensus, decentralization, signatures or ownership guarantees.

## Optional Ethereum-compatible transaction anchoring

Create an unsigned wallet transaction to embed a chosen **local ledger block hash** (32 bytes) in EVM transaction calldata. No smart contract deployment is required.

```bash
omniforge blockchain anchor --project . \
  --height 0 \
  --wallet 0x1111111111111111111111111111111111111111 \
  --chain-id 1337
```

The command outputs a JSON object with `unsigned_transaction` fields:

```json
{
  "from": "0x1111111111111111111111111111111111111111",
  "to": "0x1111111111111111111111111111111111111111",
  "value": "0x0",
  "data": "0x<64-character-block-sha256>",
  "chainId": "0x539"
}
```

The example address and chain ID are **illustrative**. For a real network, supply your own public wallet address and correct network chain ID. Check that the transaction's `to` is the same wallet, `value` is zero, and `data` matches the output exactly. Use a wallet or your existing transaction workflow to sign and broadcast manually. **OmniForge does not handle wallet keys or submit transactions.** An on-chain transaction still consumes network gas and may be irreversible.

After the wallet returns a transaction hash, verify it through a trusted JSON-RPC provider:

```bash
omniforge blockchain verify-anchor --project . \
  --height 0 \
  --wallet 0x1111111111111111111111111111111111111111 \
  --chain-id 1337 \
  --rpc-url http://127.0.0.1:8545 \
  --tx-hash 0xYOUR_64_HEX_TRANSACTION_HASH \
  --min-confirmations 3
```

The verifier compares chain ID, transaction hash, sender/recipient, **exact 32-byte calldata**, receipt status, mined block hash and confirmations. A mismatched record, chain, wallet, transaction, reverted transaction or insufficient confirmations returns a non-success result. The RPC verifier is **read-only** and accepts remote **HTTPS** or **loopback-only HTTP**.

**Reality check:** the results come from your RPC provider. OmniForge does not independently validate network consensus, detect all RPC lies or guarantee finality against chain reorganizations. Publicly anchoring the digest proves that the digest appears in a confirmed transaction; it does not certify the author, safety or contents of files.

## Real EVM integration test

In CI, OmniForge boots **disposable Ganache (chain ID 1337)**, mines a 0-value self-transaction containing the ledger hash, then verifies it through the genuine EVM JSON-RPC interface. It also checks that the same transaction cannot anchor a different ledger height.

```bash
# Only on disposable test networks! Requires Node.js, npm and Python.
npm install --no-save --no-package-lock --ignore-scripts ganache@7.9.2
node_modules/.bin/ganache --server.host 127.0.0.1 --server.port 8545 --chain.chainId 1337 &
OMNIFORGE_CHAIN_LIVE=1 python -m pytest -q tests/test_blockchain_evm.py
```

Unlike live network usage, this test uses simulated local currency and an unlocked **testing-only** wallet.

## Security and privacy

## MCP integration (read-only)

AI coding assistants connected via `omniforge mcp` can call `omniforge_chain_verify` and `omniforge_chain_proof` to inspect a project ledger. These tools **cannot** record new entries, sign wallets, submit transactions or access private keys. Use the CLI locally for recording and preparing unsigned anchor payloads.


- Never publish private keys, recovery phrases or RPC credentials. OmniForge does not ask for them.
- Never commit `.omniforge/` unless you explicitly intend to expose timestamps, notes and record hashes.
- External EVM transactions reveal sender address and data permanently to network observers. No file contents are published by OmniForge.
- Hashes alone are not digital signatures; on-chain anchoring does not verify code authorship or quality.
- Avoid hostile worktrees with concurrent attackers; path checks cannot eliminate all TOCTOU filesystem races.
- To audit a project's contents, prefer `omniforge blockchain verify --check-current` before preparing an anchor.
