"""Explicit operator interfaces. Default action never contacts a network."""
import argparse
import json
import sys
from pathlib import Path

from .api import ACKNOWLEDGEMENT, paid_once
from .budget import Ledger
from .core import SCOPE, cases, compare_snapshot, validate_receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description="QSOL CHAOS comparative security pilot")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("dry-run", help="print approved scope and cases; no network")
    comparator = commands.add_parser("compare", help="inspect a caller-provided source snapshot without execution")
    comparator.add_argument("--repo", required=True)
    comparator.add_argument("--sha", required=True)
    comparator.add_argument("--path", required=True)
    comparator.add_argument("--snapshot", type=Path, required=True)
    verifier = commands.add_parser("verify", help="verify a generated offline candidate receipt")
    verifier.add_argument("file", type=Path)
    run = commands.add_parser("paid-once", help="explicit single paid API request, no tools")
    run.add_argument("--case", required=True)
    run.add_argument("--reviewed-evidence", type=Path, required=True)
    run.add_argument("--ack", required=True)
    run.add_argument("--state-dir", type=Path, default=Path(".chaos-state"))
    args = parser.parse_args(argv)
    try:
        if args.command == "dry-run":
            print(json.dumps({"status": "offline_only", "authorized_scope": SCOPE,
                              "cases": cases(), "api_calls": 0, "api_spend_usd": 0}, indent=2))
        elif args.command == "compare":
            data = compare_snapshot(args.repo, args.sha, args.path,
                                    args.snapshot.read_text(encoding="utf-8"))
            print(json.dumps(data, indent=2))
        elif args.command == "verify":
            data = json.loads(args.file.read_text(encoding="utf-8"))
            validate_receipt(data)
            print("scope and receipt format valid (source bytes not independently re-fetched)")
        elif args.command == "paid-once":
            evidence = args.reviewed_evidence.read_text(encoding="utf-8")
            result = paid_once(args.case, evidence, args.state_dir, ack=args.ack)
            print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        print("chaos pilot: {}".format(type(exc).__name__), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())