#!/usr/bin/env python3
"""Capture the source commit and immutable historical evidence boundary."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
SOURCE_COMMIT = "a8d5b1783d5f5096f00504b99f2276f0a9fbff44"
MERGES = {
    "pr_16": "22083e28949d5691731f8cf16ed80fae23899980",
    "pr_17": "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a",
    "pr_18": "ddccc1214b7a5d5942c6755ffa4da2c144d0f6ad",
    "pr_19": "1ad645e13277a28ba511cad2f6bd2f5d988894d8",
    "pr_20": SOURCE_COMMIT,
}
HISTORICAL_PATHS = [
    "evidence/SOFA-HOT-008",
    "evidence/SOFA-BAKERS-DOZEN-013",
    "evidence/LOCAL-VERIFY-001",
    "evidence/LOCAL-VERIFY-002",
    "evidence/LOCAL-VERIFY-002B",
]
IDENTITIES = {
    "codex_primary_report": "evidence/SOFA-HOT-008/WITNESSES/CODEX-001-primary/CODEX-001-REPORT.json",
    "dual_witness_report": "evidence/SOFA-HOT-008/RECONCILIATION/SOFA-HOT-008-DUAL-WITNESS-REPORT.json",
    "local_verify_001_report": "evidence/LOCAL-VERIFY-001/REPORTS/LOCAL-VERIFY-001-REPORT.json",
    "local_verify_002_report": "evidence/LOCAL-VERIFY-002/REPORT.json",
    "local_verify_002b_report": "evidence/LOCAL-VERIFY-002B/REPORT.json",
}


def run(argv: list[str]) -> dict[str, Any]:
    completed = subprocess.run(argv, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    origin = run(["git", "rev-parse", "origin/main"])
    head = run(["git", "rev-parse", "HEAD"])
    branch = run(["git", "branch", "--show-current"])
    diff = run(["git", "diff", "--name-only", "origin/main", "--", *HISTORICAL_PATHS])
    required: dict[str, Any] = {}
    for name, commit in MERGES.items():
        check = run(["git", "merge-base", "--is-ancestor", commit, "origin/main"])
        required[name] = {
            "commit": commit,
            "ancestor_of_origin_main": check["exit_code"] == 0,
            "exit_code": check["exit_code"],
        }
    baseline = {
        "campaign": "LOCAL-VERIFY-003",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_commit": SOURCE_COMMIT,
        "origin_main": origin["stdout"].strip(),
        "branch_start_head": head["stdout"].strip(),
        "branch": branch["stdout"].strip(),
        "required_merges": required,
        "historical_evidence_modified": bool(diff["stdout"].strip()),
        "frozen_collection_diff": diff["stdout"].splitlines(),
        "known_frozen_identities": {
            name: {
                "path": relative,
                "bytes": (REPOSITORY / relative).stat().st_size,
                "sha256": sha256(REPOSITORY / relative),
            }
            for name, relative in IDENTITIES.items()
        },
        "commands": {
            "origin_main": origin,
            "head": head,
            "branch": branch,
            "historical_diff": diff,
        },
    }
    valid = (
        origin["stdout"].strip() == SOURCE_COMMIT
        and head["stdout"].strip() == SOURCE_COMMIT
        and branch["stdout"].strip() == "evidence/local-verify-003-ytdlp-caption-selection"
        and all(item["ancestor_of_origin_main"] for item in required.values())
        and not baseline["historical_evidence_modified"]
    )
    baseline["valid"] = valid
    (ROOT / "BASELINE.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
