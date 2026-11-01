"""Offline operator interfaces; no paid request or network path."""
import argparse
import json
import sys
from pathlib import Path

from .api import plan_review
from .core import SCOPE, cases, compare_snapshot, validate_receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description="QSOL CHAOS offline comparative security pilot")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("dry-run", help="print approved scope and cases; no network")
    comparator = commands.add_parser("compare", help="inspect exact bytes of a supplied source snapshot")
    comparator.add_argument("--repo", required=True)
    comparator.add_argument("--sha", required=True)
    comparator.add_argument("--path", required=True)
    comparator.add_argument("--snapshot", type=Path, required=True)
    verifier = commands.add_parser("verify", help="verify a generated offline candidate receipt")
    verifier.add_argument("file", type=Path)
    planner = commands.add_parser("plan-review", help="estimate a hypothetical review entirely offline")
    planner.add_argument("--case", required=True)
    planner.add_argument("--reviewed-evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "dry-run":
            print(json.dumps({"status": "offline_only", "authorized_scope": SCOPE,
                              "cases": cases(), "api_calls": 0, "api_spend_usd": 0}, indent=2))
        elif args.command == "compare":
            data = compare_snapshot(args.repo, args.sha, args.path,
                                    args.snapshot.read_bytes())
            print(json.dumps(data, indent=2))
        elif args.command == "verify":
            data = json.loads(args.file.read_text(encoding="utf-8"))
            validate_receipt(data)
            print("scope and receipt format valid (source bytes not independently re-fetched)")
        elif args.command == "plan-review":
            evidence = args.reviewed_evidence.read_bytes().decode("utf-8")
            print(json.dumps(plan_review(args.case, evidence), indent=2))
        return 0
    except (ValueError, UnicodeError, OSError, RuntimeError, KeyError) as exc:
        print("chaos pilot: {}".format(type(exc).__name__), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
