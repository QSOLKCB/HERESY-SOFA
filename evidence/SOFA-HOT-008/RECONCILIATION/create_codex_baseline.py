#!/usr/bin/env python3
"""Create the Codex baseline without opening or naming any Monica archive member."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/trent/SOFA-HOT-008")
PRIMARY = WORKSPACE / "CODEX-001-independent-20261104T162141Z"
ALTERNATE = WORKSPACE / "CODEX-001"
OUTPUT = WORKSPACE / "RECONCILIATION" / "CODEX-BASELINE.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path, root):
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "mode": oct(path.stat().st_mode & 0o777),
        "mtime_ns": path.stat().st_mtime_ns,
    }


def verify_primary_ledger():
    ledger = PRIMARY / "SHA256SUMS.txt"
    checked = []
    for line in ledger.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        expected_hash, expected_size, relative = line.split("  ", 2)
        path = PRIMARY / relative
        if not path.is_file():
            raise RuntimeError(f"primary ledger missing file: {relative}")
        if path.stat().st_size != int(expected_size):
            raise RuntimeError(f"primary ledger size mismatch: {relative}")
        if sha256(path) != expected_hash:
            raise RuntimeError(f"primary ledger hash mismatch: {relative}")
        checked.append(relative)
    return checked


def verify_standard_ledger(root):
    ledger = root / "SHA256SUMS.txt"
    checked = []
    for line in ledger.read_text().splitlines():
        if not line:
            continue
        expected_hash, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"alternate ledger missing file: {relative}")
        if sha256(path) != expected_hash:
            raise RuntimeError(f"alternate ledger hash mismatch: {relative}")
        checked.append(relative)
    return checked


def verify_alternate_inventory():
    manifest = json.loads((ALTERNATE / "ARTIFACTS.json").read_text())
    checked = []
    for entry in manifest["files"]:
        path = ALTERNATE / entry["path"]
        if not path.is_file():
            raise RuntimeError(f"alternate inventory missing file: {entry['path']}")
        if path.stat().st_size != entry["bytes"]:
            raise RuntimeError(f"alternate inventory size mismatch: {entry['path']}")
        if sha256(path) != entry["sha256"]:
            raise RuntimeError(f"alternate inventory hash mismatch: {entry['path']}")
        checked.append(entry["path"])
    return manifest, checked


def main():
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite existing baseline: {OUTPUT}")

    primary_checked = verify_primary_ledger()
    alternate_checked = verify_standard_ledger(ALTERNATE)
    alternate_manifest, alternate_inventory_checked = verify_alternate_inventory()

    primary_report = json.loads((PRIMARY / "CODEX-001-REPORT.json").read_text())
    primary_environment = json.loads((PRIMARY / "environment.json").read_text())
    primary_commands = json.loads((PRIMARY / "COMMAND-LOG.json").read_text())
    alternate_report = json.loads((ALTERNATE / "CODEX-001-REPORT.json").read_text())
    alternate_validation = json.loads((ALTERNATE / "validation.json").read_text())

    source_files = [identity(path, PRIMARY) for path in sorted(PRIMARY.glob("CASE-*/source.json"))]
    receipts = []
    for path in sorted(PRIMARY.glob("CASE-*/receipt.json")):
        data = json.loads(path.read_text())
        item = identity(path, PRIMARY)
        item.update({
            "case": data.get("case"),
            "process_exit_code": data.get("process_exit_code"),
            "started_utc": data.get("started_utc"),
            "finished_utc": data.get("finished_utc"),
            "failed_checks": [check.get("name") for check in data.get("checks", []) if not check.get("passed")],
        })
        receipts.append(item)

    baseline = {
        "schema": "SOFA-HOT-008-CODEX-BASELINE-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Freeze Codex witness identity before any Monica archive discovery or consultation.",
        "determination": {
            "state": "TWO_FINALIZED_CODEX_PACKAGES",
            "primary_for_reconciliation": PRIMARY.name,
            "primary_reason": "This is the read-only package explicitly cited as the completed evidence package in the prior Codex handoff; its report records the actual package path and finalization time.",
            "alternate": ALTERNATE.name,
            "alternate_treatment": "Separately finalized concurrent Codex package. Integrity-verified and retained as auxiliary Codex evidence, not mislabeled as Monica or as a preliminary failure.",
            "ambiguity_disclosed": True,
        },
        "independence_boundary": {
            "monica_archive_discovered_before_this_record": False,
            "monica_archive_members_listed_before_this_record": False,
            "monica_findings_read_before_this_record": False,
            "procedural_basis": "No command in this reconciliation session addressed MONICA-001 before this baseline writer. The primary report also self-declares Monica reports/code unused.",
            "cryptographic_limit": "This establishes the custodian's ordered workflow and pre-existing witness timestamps; it cannot prove what unrelated external processes may have read.",
            "primary_self_declaration": primary_report.get("independence"),
            "alternate_self_declaration": alternate_report.get("independence"),
        },
        "primary": {
            "root": str(PRIMARY),
            "report": identity(PRIMARY / "CODEX-001-REPORT.json", PRIMARY),
            "review": identity(PRIMARY / "CODEX-001-REVIEW.md", PRIMARY),
            "environment": identity(PRIMARY / "environment.json", PRIMARY),
            "command_log": identity(PRIMARY / "COMMAND-LOG.json", PRIMARY),
            "ledger": identity(PRIMARY / "SHA256SUMS.txt", PRIMARY),
            "ledger_entry_count": len(primary_checked),
            "ledger_verification": "PASS",
            "source_snapshots": source_files,
            "execution_receipts": receipts,
            "all_final_receipts_exit_zero": all(item["process_exit_code"] == 0 for item in receipts),
            "all_final_receipts_have_no_failed_checks": all(not item["failed_checks"] for item in receipts),
            "report_finalized_utc": primary_report["execution_window_utc"]["finalized"],
            "actual_environment": primary_report["environment"],
            "raw_environment_capture_utc": primary_environment.get("captured_utc"),
            "preliminary_runs_separated": {
                "source": "COMMAND-LOG.json",
                "first_parallel_run": next(
                    (item for item in primary_commands["attempts"] if item.get("phase") == "first-parallel-run"),
                    None,
                ),
                "final_exit_codes": primary_commands["final_case_exit_codes"],
            },
        },
        "alternate_codex_package": {
            "root": str(ALTERNATE),
            "report": identity(ALTERNATE / "CODEX-001-REPORT.json", ALTERNATE),
            "review": identity(ALTERNATE / "CODEX-001-REVIEW.md", ALTERNATE),
            "artifact_manifest": identity(ALTERNATE / "ARTIFACTS.json", ALTERNATE),
            "ledger": identity(ALTERNATE / "SHA256SUMS.txt", ALTERNATE),
            "ledger_entry_count": len(alternate_checked),
            "ledger_verification": "PASS",
            "manifest_entry_count": len(alternate_inventory_checked),
            "manifest_verification": "PASS",
            "manifest_seal_metadata": alternate_manifest.get("seal_metadata"),
            "assembled_at_utc": alternate_report.get("assembled_at_utc"),
            "validation": alternate_validation,
            "execution_summary": alternate_report.get("summaries"),
            "preliminary_history_refs": ["harness-history.json", "finalization-attempts/01-receipt.json"],
        },
        "baseline_status": "FROZEN_BEFORE_MONICA_INSPECTION",
    }

    OUTPUT.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
    os.chmod(OUTPUT, 0o444)
    print(json.dumps({
        "output": str(OUTPUT),
        "bytes": OUTPUT.stat().st_size,
        "sha256": sha256(OUTPUT),
        "primary_report_sha256": baseline["primary"]["report"]["sha256"],
        "alternate_report_sha256": baseline["alternate_codex_package"]["report"]["sha256"],
        "status": baseline["baseline_status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
