#!/usr/bin/env python3
"""CODEX-RECONCILIATION-TEST: reproduce Monica's TypeVarTuple runtime observation."""

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Generic, TypeVar, TypeVarTuple, Unpack

T = TypeVar("T")
Ts = TypeVarTuple("Ts")


class Fixed(Generic[Unpack[Ts]]):
    pass


class Foo(Generic[T]):
    pass


def capture(callable_):
    try:
        value = callable_()
        return {"accepted": True, "repr": repr(value),
                "runtime_type": f"{type(value).__module__}.{type(value).__qualname__}"}
    except Exception as exc:
        return {"accepted": False, "exception_type": type(exc).__name__, "message": str(exc)}


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    fixed = capture(lambda: Fixed[int, ...])
    foo = capture(lambda: Foo[int, ...])
    checks = [
        {"name": "typevartuple_runtime_accepts_ellipsis", "passed": fixed["accepted"] is True,
         "actual": fixed, "expected": {"accepted": True}},
        {"name": "single_typevar_runtime_rejects_two_arguments", "passed": foo["accepted"] is False,
         "actual": foo, "expected": {"accepted": False, "exception_type": "TypeError"}},
        {"name": "single_typevar_exception_is_typeerror",
         "passed": foo.get("exception_type") == "TypeError",
         "actual": foo.get("exception_type"), "expected": "TypeError"},
    ]
    passed = all(item["passed"] for item in checks)
    receipt = {
        "experiment_id": "CODEX-RECONCILIATION-TEST-CASE-06-TYPEVARTUPLE",
        "status": "PASS" if passed else "FAIL",
        "scope": "CPython runtime only; no Pyright inference",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python typevartuple_runtime.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "checks": checks,
        "reconciliation": {
            "monica_observation_reproduced": passed,
            "interpretation": "CPython runtime accepts Ellipsis inside a TypeVarTuple argument pack but rejects two arguments for a one-TypeVar generic. This does not establish Pyright acceptance or refute a checker-specific rejection claim.",
        },
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"experiment_id": receipt["experiment_id"], "passed": passed,
                      "checks": len(checks)}, sort_keys=True))
    return receipt["process_exit_code"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
