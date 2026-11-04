#!/usr/bin/env python3
"""Run final LOCAL-VERIFY-001 fixtures and preserve exact execution receipts."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "PYTHON-TYPING"
SPN2_DIR = ROOT / "SPN2-SCHEDULER"
RECEIPTS = ROOT / "RECEIPTS"
EXECUTION_RECEIPT = RECEIPTS / "LOCAL-VERIFY-001-EXECUTION.json"
DETERMINISM_RECEIPT = ROOT / "CROSS-CHECKS" / "determinism.json"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def source_inventory() -> list[dict[str, Any]]:
    paths = sorted(
        [*PYTHON_DIR.glob("*.py"), *SPN2_DIR.glob("*.py"), Path(__file__).resolve()],
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest_file(path),
        }
        for path in paths
    ]


def run_command(argv: list[str], *, label: str) -> dict[str, Any]:
    started = utc_now()
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    result = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    finished = utc_now()
    return {
        "label": label,
        "argv": argv,
        "cwd": str(ROOT),
        "environment_overrides": {"PYTHONHASHSEED": "0"},
        "started_at_utc": started,
        "finished_at_utc": finished,
        "exit_code": result.returncode,
        "stdout_bytes": len(result.stdout),
        "stdout_sha256": digest_bytes(result.stdout),
        "stdout": result.stdout.decode("utf-8", errors="replace"),
        "stderr_bytes": len(result.stderr),
        "stderr_sha256": digest_bytes(result.stderr),
        "stderr": result.stderr.decode("utf-8", errors="replace"),
    }


def write_text(path: Path, text: str) -> dict[str, Any]:
    path.write_text(text, encoding="utf-8")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest_file(path),
    }


def write_json(path: Path, value: Any) -> dict[str, Any]:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest_file(path),
    }


def require(condition: bool, message: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"check": message, "passed": bool(condition)})
    if not condition:
        raise AssertionError(message)


def main() -> int:
    started = utc_now()
    before = source_inventory()
    checks: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    # Safety gate: experiment sources must not import network clients.
    forbidden = (
        "import socket", "from socket", "urllib.request", "requests",
        "httpx", "aiohttp", "archive.org", "discord.com",
    )
    safety_hits: dict[str, list[str]] = {}
    for item in before:
        if not item["path"].startswith(("PYTHON-TYPING/", "SPN2-SCHEDULER/")):
            continue
        path = ROOT / item["path"]
        text = path.read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in text]
        if hits:
            safety_hits[item["path"]] = hits
    require(not safety_hits, "experiment sources contain no forbidden network client tokens", checks)

    verbatim = run_command(
        [sys.executable, str(PYTHON_DIR / "generic_alias_verbatim.py")],
        label="A1-verbatim-GenericAlias-reply",
    )
    commands.append(verbatim)
    outputs.append(write_text(PYTHON_DIR / "generic-alias-verbatim.stdout.txt", verbatim["stdout"]))
    outputs.append(write_text(PYTHON_DIR / "generic-alias-verbatim.stderr.txt", verbatim["stderr"]))
    require(verbatim["exit_code"] == 1, "A1 verbatim fixture exits 1", checks)
    require(
        "TypeError: type 'types.GenericAlias' is not subscriptable" in verbatim["stderr"],
        "A1 preserves the exact GenericAlias TypeError", checks,
    )

    runtime_runs = [
        run_command(
            [sys.executable, str(PYTHON_DIR / "runtime_investigation.py")],
            label=f"A-B-native-runtime-fresh-process-{index}",
        )
        for index in (1, 2)
    ]
    commands.extend(runtime_runs)
    runtime_values = [json.loads(item["stdout"]) for item in runtime_runs]
    outputs.append(write_json(PYTHON_DIR / "runtime-result.json", runtime_values[0]))
    require(all(item["exit_code"] == 0 for item in runtime_runs), "both native runtime executions exit 0", checks)
    require(all(item["failed_assertion_count"] == 0 for item in runtime_values), "both native runtime assertion sets pass", checks)
    require(runtime_runs[0]["stdout_sha256"] == runtime_runs[1]["stdout_sha256"], "native runtime output is byte-deterministic across fresh processes", checks)

    mypy_specs = [
        ("A4-genericalias-positive", "genericalias_static_positive.py", 0),
        ("A4-genericalias-negative", "genericalias_static_fixture.py", 1),
        ("B-mypy-mismatch", "dataclass_mismatch_fixture.py", 1),
        ("B-mypy-ignore-unsound", "dataclass_unsound_fixture.py", 0),
        ("B-mypy-sound-designs", "dataclass_sound_fixture.py", 0),
    ]
    mypy_results: dict[str, dict[str, Any]] = {}
    for label, filename, expected_exit in mypy_specs:
        item = run_command(
            ["mypy", "--strict", "--show-error-codes", str(PYTHON_DIR / filename)],
            label=label,
        )
        commands.append(item)
        mypy_results[label] = item
        outputs.append(write_text(PYTHON_DIR / f"{label}.txt", item["stdout"] + item["stderr"]))
        require(item["exit_code"] == expected_exit, f"{label} has expected exit {expected_exit}", checks)

    require("Unexpected \"...\"  [misc]" in mypy_results["A4-genericalias-negative"]["stdout"], "mypy 1.19.1 rejects literal ellipsis in the TypeVarTuple fixture", checks)
    require("expects 1 type argument, but 2 given" in mypy_results["A4-genericalias-negative"]["stdout"], "mypy rejects invalid Single argument count", checks)
    require("not generic and not indexable" in mypy_results["A4-genericalias-negative"]["stdout"], "mypy does not infer custom runtime subscription as a generic", checks)
    require("Incompatible types in assignment" in mypy_results["B-mypy-mismatch"]["stdout"], "mypy reports the unsuppressed factory mismatch", checks)
    require('Revealed type is "dataclass_unsound_fixture.C2"' in mypy_results["B-mypy-ignore-unsound"]["stdout"], "mypy reveals C2 after the targeted ignore", checks)

    spn2_runs = [
        run_command(
            [sys.executable, str(SPN2_DIR / "run_spn2_investigation.py")],
            label=f"C-offline-scheduler-fresh-process-{index}",
        )
        for index in (1, 2)
    ]
    commands.extend(spn2_runs)
    spn2_values = [json.loads(item["stdout"]) for item in spn2_runs]
    outputs.append(write_json(SPN2_DIR / "scheduler-result.json", spn2_values[0]))
    require(all(item["exit_code"] == 0 for item in spn2_runs), "both scheduler executions exit 0", checks)
    require(all(item["failed_assertion_count"] == 0 for item in spn2_values), "both scheduler assertion sets pass", checks)
    require(spn2_runs[0]["stdout_sha256"] == spn2_runs[1]["stdout_sha256"], "scheduler output is byte-deterministic across fresh processes", checks)

    after = source_inventory()
    require(before == after, "source hashes and byte sizes are unchanged during final execution", checks)

    determinism = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "checked_at_utc": utc_now(),
        "fresh_process_pairs": {
            "python_typing_runtime": {
                "run_1_stdout_sha256": runtime_runs[0]["stdout_sha256"],
                "run_2_stdout_sha256": runtime_runs[1]["stdout_sha256"],
                "byte_identical": runtime_runs[0]["stdout_sha256"] == runtime_runs[1]["stdout_sha256"],
            },
            "spn2_scheduler": {
                "run_1_stdout_sha256": spn2_runs[0]["stdout_sha256"],
                "run_2_stdout_sha256": spn2_runs[1]["stdout_sha256"],
                "byte_identical": spn2_runs[0]["stdout_sha256"] == spn2_runs[1]["stdout_sha256"],
            },
        },
        "source_unchanged": before == after,
        "source_inventory": before,
    }
    outputs.append(write_json(DETERMINISM_RECEIPT, determinism))

    receipt = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "execution_class": ["EXECUTED_NATIVE", "EXECUTED_SIMULATED"],
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "orchestrator": {
            "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "sha256": digest_file(Path(__file__).resolve()),
            "invocation": [
                "uv", "run", "--no-project", "--offline",
                "--no-managed-python", "python", str(Path(__file__).resolve()),
            ],
            "python": platform.python_version(),
        },
        "dependency_versions": {
            "mypy": subprocess.run(
                ["mypy", "--version"], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False,
            ).stdout.strip(),
            "pyright": "NOT_TESTED: executable and verified local cache absent",
            "mypy_2_3_1": "NOT_TESTED: executable and verified local cache absent",
        },
        "seed": 26051105,
        "network_access": False,
        "real_sleep": False,
        "source_inventory_before_and_after_identical": before == after,
        "sources": before,
        "outputs": outputs,
        "checks": checks,
        "check_count": len(checks),
        "failed_check_count": sum(not item["passed"] for item in checks),
        "native_runtime_assertion_count": runtime_values[0]["assertion_count"],
        "native_runtime_negative_control_count": runtime_values[0]["negative_control_count"],
        "simulated_scheduler_assertion_count": spn2_values[0]["assertion_count"],
        "simulated_scheduler_negative_control_count": spn2_values[0]["negative_control_count"],
        "total_runtime_assertion_count": runtime_values[0]["assertion_count"] + spn2_values[0]["assertion_count"],
        "total_runtime_negative_control_count": runtime_values[0]["negative_control_count"] + spn2_values[0]["negative_control_count"],
        "expected_failure_command_count": 3,
        "commands": commands,
        "limitations": [
            "Pyright 1.1.414, basedpyright, and mypy 2.3.1 were absent and were not installed.",
            "SPN2 results are offline simulations and make no claim about live Internet Archive behavior.",
            "CPython runtime acceptance is not static-checker acceptance.",
        ],
    }
    EXECUTION_RECEIPT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "receipt": str(EXECUTION_RECEIPT),
        "receipt_sha256": digest_file(EXECUTION_RECEIPT),
        "commands": len(commands),
        "checks": len(checks),
        "assertions": receipt["total_runtime_assertion_count"],
        "negative_controls": receipt["total_runtime_negative_control_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
