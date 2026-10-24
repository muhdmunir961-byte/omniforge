# OF-Provenance v2 — Panduan teknikal dan pengguna (Bahasa Melayu)

**Status:** implemented as an optional OmniForge module. Legacy command **omniforge blockchain** (v1) remains supported. New commands: **ofprov** and **omniforge provenance**.

**Purpose:** local SHA-256 hash-chain for tamper-evident developer project snapshots and optional unsigned EVM hash anchoring. It is NOT a decentralized blockchain, cryptocurrency, wallet, proof of authorship, malware scanner, or a guarantee of security.

## A. Scope and architecture

~~~text
project files → strict scanner → per-file SHA-256 → policy + snapshot digest
     → append-only logical chain.jsonl → strict verification / audit
                                    ↘ EVM unsigned tx builder
                                       → user-approved external wallet
                                       → EVM network → read-only JSON-RPC check
                                       → anchors.jsonl (untrusted local receipt history)
~~~

The CLI, scanner, ledger, read-only EVM verifier and test packages are separated into:
- src/omniforge/provenance_v2_policy.py: canonical hashes, safe paths, file scanner, resource caps.
- src/omniforge/provenance_v2.py: initialization, snapshots, verification, audit, legacy migration, external backup, optional receipt journal.
- src/omniforge/provenance_v2_evm.py: EVM calldata builder and read-only verification.
- src/omniforge/provenance_v2_cli.py: command-line interface.
- docs/PROVENANCE_V2_SCHEMA.json: formal record schema.
- tests/test_provenance_v2.py and tests/test_blockchain_evm.py: unit, security and disposable EVM tests.

## B. Local file layout

~~~text
your-project/
  src/
  .of-provenance/
    config.json
    chain.jsonl
    anchors.jsonl
    lock
    legacy-v1-chain.jsonl       # only after explicit migration
    legacy-v1-anchors.jsonl     # when available during migration
~~~

This folder is excluded from the scanner and normally gitignored. Never assume a local ledger is immutable: a filesystem administrator can replace the entire history.

## C. Stack, dependencies and assumptions

Python 3.11+ is supported. Runtime dependencies are all from Python's standard library (argparse, json, pathlib, hashlib, os, uuid, urllib). Unit tests use pytest. EVM integration CI uses Ganache on a disposable local chain with simulated value and test-only unlocked accounts. Normal operation never requires a cryptocurrency library, real wallet or network.

On POSIX, scanner files are opened using descriptor-relative NOFOLLOW checks and writer locks use fcntl. Windows fallback is not yet proven equally resistant to concurrent malicious path-swap races. Timestamps reflect the host machine clock, not an authenticated time source.

Limits (fail closed): maximum 3,000 files/snapshot, 20 MB/file, 512 MB total snapshot bytes, 10 MB ledger and 10,000 records. There is no automatic history pruning. If full, export and verify a trusted backup before starting a new independent project.

Default exclusions include .git, .of-provenance, .omniforge, .venv, node_modules, __pycache__, .pytest_cache, .env and .env.*. Excluded files are outside the declared integrity scope.

## D. Ledger schema and cryptography

A single line of chain.jsonl is one complete UTF-8 JSON object, ending in a newline. Duplicate keys and unsupported fields are rejected.

Required: version=2, seq, timestamp (UTC Z), project_id (canonical UUIDv4), file_hashes, snapshot_hash, policy, policy_hash, prev_hash, entry_hash, anchor_status="not_requested". Optional: note (max 160 characters). A genesis record after legacy migration may also contain legacy_ref.

Algorithms:
- canonical(x): UTF-8 JSON with sorted keys, compact separators, ensure_ascii=False and allow_nan=False.
- snapshot_hash: SHA256(ASCII "OF-SNAPSHOT-v2" + NUL + canonical(file_hashes)).
- policy_hash: SHA256(ASCII "OF-POLICY-v2" + NUL + canonical(full_policy)).
- entry_hash: SHA256(ASCII "OF-ENTRY-v2" + NUL + canonical(record WITHOUT entry_hash)).
- Genesis prev_hash: 64 zero hex digits. Each subsequent prev_hash equals the preceding entry_hash.

The full immutable scan policy is stored inside EVERY record, not merely its hash. Strict verification checks every schema field, relative path, snapshot digest, policy digest, project UUID, sequence and hash link.

Anchor status remains "not_requested" on the immutable snapshot. Verified RPC events may be stored separately in anchors.jsonl using --save-receipt; journal entries have their own linked hashes. Even an intact local journal must NEVER be treated as fresh on-chain proof. Recheck the transaction through trusted RPC.

## E. Installation and real CLI commands

~~~bash
git clone https://github.com/muhdmunir961-byte/omniforge.git
cd omniforge
python -m pip install -e .
ofprov --help
~~~

Initialize a project:
~~~bash
ofprov init --project .
~~~

Snapshot, including scan policy:
~~~bash
ofprov snapshot --project . --note "pre-release"
~~~

Verify ledger and current files:
~~~bash
ofprov verify --project . --check-files
~~~

Check trusted EXTERNAL checkpoint (provide both fields):
~~~bash
ofprov verify --project . --check-files --expected-seq 2 --expected-head YOUR_64_HEX_HASH
~~~

Produce audit JSON (missing, added, modified, policy_changed and warnings):
~~~bash
ofprov audit --project .
~~~

Inspect an old record and policy:
~~~bash
ofprov proof --project . --seq 0
~~~

Changing config.json's scanning policy requires explicit acceptance:
~~~bash
ofprov snapshot --project . --allow-policy-change
~~~

Backup must be outside the project:
~~~bash
ofprov backup --project . --out ../my-offline-backup-001
~~~

The backup includes chain, config and migration evidence plus checkpoint.json recording project_id, head and seq. Copy these to separately controlled storage. Simply storing them on the same writable computer is not independent attestation.

## F. Migration from legacy OmniForge v1

Older version 1 uses different fields (height, previous, snapshot, hash). DO NOT convert these records in place or rename old hashes.

~~~bash
ofprov migrate --project .             # dry-run preview
ofprov migrate --project . --approve   # copy old chain and optional anchor metadata
ofprov snapshot --project .            # NEW v2 genesis referencing old head
~~~

The original .omniforge/chain.jsonl is untouched. Byte-identical copies are placed under .of-provenance and linked by legacy_ref (v1 head, original ledger SHA-256, entry count, optional anchor metadata SHA-256). Old on-chain v1 proofs must still be verified using the old v1 commands. Corruption of the preserved v1 backup causes v2 verification to fail.

If migration or initialization is interrupted, the system refuses to overwrite partial state. Investigate and preserve evidence before manually recovering from backups.

## G. Optional Ethereum-compatible anchoring

The CLI prepares an UNSIGNED zero-value transaction addressed from the user's PUBLIC wallet address back to the same address. Its calldata contains ONLY 0x + entry_hash. No signing, wallet import, broadcast, private key or seed phrase is implemented.

~~~bash
ofprov anchor --project . --seq 0 --chain-id 1337 --wallet 0x1111111111111111111111111111111111111111 --prepare --ack-public-data
~~~

This requires explicit acknowledgment of public data even though the command itself does not broadcast. Review the wallet, correct chain ID, value=0, calldata and potential gas fee before approving anything in your independent wallet. Addresses and calldata on a public chain may remain visible permanently.

After YOU sign and broadcast externally:
~~~bash
ofprov anchor --project . --seq 0 --chain-id 1337 --wallet 0x1111111111111111111111111111111111111111 --verify-tx 0xYOUR_REAL_TRANSACTION_HASH --rpc-url http://127.0.0.1:8545 --confirmations 3
~~~

Option --save-receipt stores the historical RPC result locally; it does not make the proof independently trustworthy. For external RPC hosts, HTTPS is mandatory. Provider responses and confirmations are not independent consensus verification, and chain reorganizations remain possible.

## H. Security threat model

| Threat | Limit | Mitigation |
|---|---|---|
| All ledger records rewritten | Local-only verifier may accept recalculated hashes | Verify against externally trusted seq AND head |
| Fake JSON with duplicate/extra fields | Rehashed malicious content | Strict schema and duplicate-key rejection |
| Silent scan policy modification | Different files can be skipped | Full immutable policy history and --allow-policy-change |
| File deletion/addition/change | Current project differs from snapshot | --check-files and audit |
| Symlink / special file / traversal | Escape project boundaries | NOFOLLOW, relative path validation, file type checks |
| Partial/truncated JSONL | History corrupted | Require complete records and consistent links |
| Anchors journal altered | False local verification claim | Linked journal hashes; always re-check live RPC |
| V1 migration destroys previous attestation | Old transaction no longer matches | Copy-only legacy backup, old hashes preserved |
| RPC provider lies or chain reorganizes | Incorrect or stale status | Trusted RPC, confirmations, cross-check externally |
| Ransomware or full host control | Can destroy all local evidence | Offsite backup and independently trusted checkpoint |

## I. Required user warnings

> Ledger setempat boleh diubah oleh sesiapa yang ada akses fail.

> Anchoring ke EVM tidak membuktikan pemilikan atau keselamatan kod.

> Jangan masukkan rahsia dalam nota anchor.

> Data on-chain kekal kelihatan selama-lamanya.

Never put secrets in notes or on-chain data. The local record can expose filenames and timestamps. The digest does not recover source code: use Git and real source backups.

## J. Verification pseudocode

~~~python
def domain_hash(name, obj):
    return sha256(name + b"\x00" + canonical(obj)).hexdigest()

for seq, entry in enumerate(strict_jsonl_read(ledger)):
    validate_schema_uuid_paths_policy_and_types(entry)
    assert entry["seq"] == seq
    assert entry["prev_hash"] == previous
    assert entry["policy_hash"] == domain_hash(b"OF-POLICY-v2", entry["policy"])
    assert entry["snapshot_hash"] == domain_hash(b"OF-SNAPSHOT-v2", entry["file_hashes"])
    payload = {k:v for k,v in entry.items() if k != "entry_hash"}
    assert entry["entry_hash"] == domain_hash(b"OF-ENTRY-v2", payload)
    previous = entry["entry_hash"]

assert entries[externally_trusted_seq]["entry_hash"] == externally_trusted_head
~~~

The implementation also limits file size, locks writes, refuses truncation and verifies archived migration evidence.

## K/L. User FAQ, tests and deliverables

**Adakah ini blockchain sendiri?** Tidak. Ini hanya local hash-chain, optionally anchored onto an already existing EVM network.

**Perlu wallet?** Tidak untuk local records. Public-chain anchoring is optional and requires a user-controlled wallet and gas approval.

**Adakah hash membuktikan copyright?** Tidak. Digest equality only supports a bounded integrity claim.

**Boleh recover file daripada hash?** Tidak. Save versioned source backups separately.

**Adakah status verified kekal selama-lamanya?** Tidak. RPC is trusted-provider output and can change with reorganizations. Recheck live before making an important decision.

**Adakah migration rewrite v1 anchors?** Tidak. Raw backups and original head are preserved. The v2 genesis stores a reference only.

**Test plan:** unit SHA-256, invalid schema/path/UUID, chain tampering, full ledger rewrite with external head, rollback/truncation, policy changes, migration, concurrent writes, missing files, unsafe symlinks, resource limits, anchor acknowledgments, journal tampering and real local Ganache EVM receipt verification.

**Known limits:** no formal supply-chain attestation, no guaranteed immutability without an independent checkpoint, no full cross-platform race protection, no on-chain mainnet certification, no wallet custody, no proof of authorship, and no antivirus behavior.

**Release checklist:** all Python matrix tests pass, disposable EVM integration passes, documentation matches CLI, no unsupported security claims, backup/restore procedure reviewed, and GitHub CI links refer to the final released commit.
