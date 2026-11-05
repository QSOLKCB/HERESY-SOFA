#!/usr/bin/env python3
"""Capture the complete full-repository validation output."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


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
    "-m",
    "unittest",
    "discover",
    "-s",
    "tests",
    "-v",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    environment = {
        "HOME": os.environ["HOME"],
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PATH": os.environ["PATH"],
        "PYTHONDONTWRITEBYTECODE": "1",
        "UV_NO_PROGRESS": "1",
    }
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
    stdout = completed.stdout
    stderr = completed.stderr
    RAW.mkdir(parents=True, exist_ok=True)
    stdout_path = RAW / "FULL-SUITE.stdout.txt"
    stderr_path = RAW / "FULL-SUITE.stderr.txt"
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    combined = (stderr + b"\n" + stdout).decode("utf-8", errors="strict")
    ran = re.search(r"Ran (\d+) tests", combined)
    skipped = re.search(r"OK \(skipped=(\d+)\)", combined)
    receipt = {
        "campaign": "LOCAL-VERIFY-003",
        "command": COMMAND,
        "cwd": "$REPOSITORY",
        "started_at_utc": started,
        "finished_at_utc": finished,
        "elapsed_ns": elapsed_ns,
        "exit_code": completed.returncode,
        "tests_run": int(ran.group(1)) if ran else None,
        "skipped": int(skipped.group(1)) if skipped else 0,
        "stdout": {
            "path": "RAW/FULL-SUITE.stdout.txt",
            "bytes": len(stdout),
            "sha256": digest(stdout),
        },
        "stderr": {
            "path": "RAW/FULL-SUITE.stderr.txt",
            "bytes": len(stderr),
            "sha256": digest(stderr),
        },
        "offline_arguments": True,
        "external_service_access_authorized": False,
        "sandbox_override_reason": "The existing RETRO regression requires a local socketpair operation denied by the managed sandbox.",
        "passed": completed.returncode == 0 and ran is not None and "FAILED" not in combined,
    }
    (RAW / "REPOSITORY-VALIDATION.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
