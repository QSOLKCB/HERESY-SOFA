#!/usr/bin/env python3
"""Capture two fresh-process executions of the offline matrix."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
RAW = ROOT / "RAW"
COMMAND = [
    "uv",
    "run",
    "--no-project",
    "--offline",
    "--no-managed-python",
    "python",
    "evidence/LOCAL-VERIFY-003/SOURCE/run_offline_matrix.py",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_inventory() -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for folder in (ROOT / "SOURCE", ROOT / "FIXTURES"):
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                inventory[path.relative_to(ROOT).as_posix()] = {
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
    return inventory


def run_once(index: int, environment: dict[str, str]) -> dict[str, Any]:
    started = now()
    before = time.monotonic_ns()
    completed = subprocess.run(
        COMMAND,
        cwd=REPOSITORY,
        env=environment,
        capture_output=True,
        check=False,
    )
    elapsed_ns = time.monotonic_ns() - before
    finished = now()
    stdout = completed.stdout.decode("utf-8", errors="strict")
    stderr = completed.stderr.decode("utf-8", errors="strict")
    return {
        "run": index,
        "command": COMMAND,
        "cwd": "$REPOSITORY",
        "started_at_utc": started,
        "finished_at_utc": finished,
        "elapsed_ns": elapsed_ns,
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
    }


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is unavailable")
    environment = {
        "HOME": os.environ["HOME"],
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PATH": os.environ["PATH"],
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_PROGRESS": "1",
    }
    before = source_inventory()
    runs = [run_once(1, environment), run_once(2, environment)]
    after = source_inventory()
    parsed: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for item in runs:
        try:
            parsed.append(json.loads(item["stdout"]))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"run {item['run']}: {exc}")
    deterministic = (
        runs[0]["stdout"] == runs[1]["stdout"]
        and runs[0]["stderr"] == runs[1]["stderr"]
    )
    successful = (
        all(item["exit_code"] == 0 for item in runs)
        and not parse_errors
        and len(parsed) == 2
        and all(item["assertions"]["failed_count"] == 0 for item in parsed)
        and deterministic
        and before == after
    )
    receipt = {
        "campaign": "LOCAL-VERIFY-003",
        "execution_scope": "offline synthetic metadata plus installed process_subtitles",
        "network_authorized": False,
        "uv_executable": "$HOME/.local/bin/uv",
        "uv_executable_bytes": Path(uv).stat().st_size,
        "uv_executable_sha256": sha256_bytes(Path(uv).read_bytes()),
        "runs": runs,
        "parse_errors": parse_errors,
        "determinism": {
            "byte_identical_stdout": runs[0]["stdout"] == runs[1]["stdout"],
            "byte_identical_stderr": runs[0]["stderr"] == runs[1]["stderr"],
            "semantic_results_identical": len(parsed) == 2 and parsed[0] == parsed[1],
        },
        "source_inventory_before": before,
        "source_inventory_after": after,
        "source_inventory_unchanged": before == after,
        "successful": successful,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "OFFLINE-EXECUTION.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if parsed:
        (RAW / "OFFLINE-RESULT.json").write_text(
            json.dumps(parsed[0], indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
