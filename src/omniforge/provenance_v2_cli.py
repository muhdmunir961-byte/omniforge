"""User-controlled OF-Provenance v2 CLI. Never signs or broadcasts EVM tx."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from . import __version__
from . import provenance_v2 as ledger
from .provenance_v2_evm import prepare, check_tx


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ofprov", description="OF-Provenance v2: local tamper-evident ledger; optional EVM proof"
    )
    p.add_argument("--version", action="version", version=f"OF-Provenance {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    for name, purpose in (
        ("init", "initialize a new v2 ledger without touching any v1 history"),
        ("migrate", "preview or copy a legacy v1 ledger without rewriting its hashes"),
        ("snapshot", "append a source-file snapshot and immutable scan policy"),
        ("verify", "verify chain structure and optionally project files/trusted checkpoint"),
        ("audit", "report changed/missing files and local security limitations"),
        ("proof", "show one immutable v2 ledger record"),
        ("anchor", "prepare an unsigned EVM tx or check an externally broadcast tx"),
        ("backup", "export ledger and trusted checkpoint to an external directory"),
    ):
        cmd = sub.add_parser(name, help=purpose)
        cmd.add_argument("--project", type=Path, default=Path.cwd())
        if name == "migrate":
            cmd.add_argument("--approve", action="store_true",
                             help="explicitly copy legacy evidence; never overwrite v1")
        elif name == "snapshot":
            cmd.add_argument("--note", default="")
            cmd.add_argument("--allow-policy-change", action="store_true")
            cmd.add_argument("--expected-head", help="current ledger tip before append")
        elif name in ("verify", "audit"):
            if name == "verify":
                cmd.add_argument("--check-files", action="store_true")
            cmd.add_argument("--expected-head", help="independently trusted block hash")
            cmd.add_argument("--expected-seq", type=int, help="sequence of trusted hash")
        elif name == "proof":
            cmd.add_argument("--seq", type=int)
        elif name == "backup":
            cmd.add_argument("--out", type=Path, required=True,
                             help="new backup directory outside the project")
        elif name == "anchor":
            cmd.add_argument("--seq", type=int)
            cmd.add_argument("--wallet", required=True, help="public wallet address only")
            cmd.add_argument("--chain-id", type=int, required=True)
            operation = cmd.add_mutually_exclusive_group(required=True)
            operation.add_argument("--prepare", action="store_true",
                                   help="prepare unsigned transaction; no network access")
            operation.add_argument("--verify-tx", help="verify wallet-submitted tx hash via read-only RPC")
            cmd.add_argument("--ack-public-data", action="store_true",
                             help="I understand calldata and wallet address may remain public")
            cmd.add_argument("--rpc-url", help="HTTPS or loopback-only HTTP")
            cmd.add_argument("--confirmations", type=int, default=1)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            result = ledger.init(args.project)
        elif args.command == "migrate":
            result = ledger.migrate(args.project, approve=args.approve)
        elif args.command == "snapshot":
            result = ledger.snapshot(
                args.project, note=args.note,
                allow_policy_change=args.allow_policy_change,
                expected_head=args.expected_head,
            )
        elif args.command == "verify":
            result = ledger.verify(
                args.project, check_files=args.check_files,
                expected_head=args.expected_head, expected_seq=args.expected_seq,
            )
        elif args.command == "audit":
            result = ledger.audit(
                args.project, expected_head=args.expected_head,
                expected_seq=args.expected_seq,
            )
        elif args.command == "proof":
            result = ledger.proof(args.project, args.seq)
        elif args.command == "backup":
            result = ledger.backup(args.project, args.out)
        elif args.command == "anchor" and args.prepare:
            result = prepare(
                args.project, seq=args.seq,
                wallet=args.wallet, chain_id=args.chain_id,
                ack_public_data=args.ack_public_data,
            )
        elif args.command == "anchor" and args.verify_tx:
            if not args.rpc_url:
                raise ValueError("--rpc-url is required with --verify-tx")
            result = check_tx(
                args.project, seq=args.seq, wallet=args.wallet,
                chain_id=args.chain_id, tx_hash=args.verify_tx,
                endpoint=args.rpc_url, min_confirmations=args.confirmations,
            )
        else:
            raise ValueError("Unknown command")
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result.get("ok", True) else 1
    except (ValueError, OSError, UnicodeError) as exc:
        print("ofprov: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
