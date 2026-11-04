#!/usr/bin/env python3
"""Validate extracted Monica evidence without executing supplied scripts."""

import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

WORKSPACE = Path("/home/trent/SOFA-HOT-008")
RECON = WORKSPACE / "RECONCILIATION"
ROOT = RECON / "MONICA-EXTRACTED-cc3d4ae960c6" / "SOFA-HOT-008" / "MONICA-001"
ARCHIVE = WORKSPACE / "MONICA-001" / "SOFA-HOT-008-MONICA-001-evidence.gz"
INGESTION = RECON / "MONICA-INGESTION-RECEIPT.json"
OUTPUT = RECON / "MONICA-ARCHIVE-INVENTORY.json"
LEDGER_PATTERN = re.compile(r"^([0-9a-f]{64})  (.+)  ([0-9]+)$")

EXPECTED_CASES = {
    "01": "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
    "02": "02c83759-175f-4e00-8b7b-8962f3ba33c4",
    "03": "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
    "04": "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
    "05": "47de513f-cd52-4b36-a43d-ec4cb89c972f",
    "06": "0b3591f6-75de-4661-a7a7-ec28193e1518",
    "07": "4a28aa43-10aa-4476-b33b-85cc91998975",
    "08": "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path, base):
    return {
        "path": path.relative_to(base).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def parse_custom_ledger():
    ledger = ROOT / "SHA256SUMS.txt"
    entries = []
    seen = set()
    for number, line in enumerate(ledger.read_text().splitlines(), 1):
        match = LEDGER_PATTERN.fullmatch(line)
        if not match:
            raise RuntimeError(f"malformed custom ledger line {number}")
        expected_hash, relative, expected_size = match.groups()
        posix = PurePosixPath(relative)
        if posix.is_absolute() or ".." in posix.parts:
            raise RuntimeError(f"unsafe ledger path: {relative}")
        normalized = posix.as_posix()
        if normalized in seen:
            raise RuntimeError(f"duplicate ledger path: {normalized}")
        seen.add(normalized)
        path = ROOT.joinpath(*posix.parts)
        if not path.is_file():
            raise RuntimeError(f"ledger-declared file missing: {normalized}")
        actual_hash = sha256(path)
        actual_size = path.stat().st_size
        entries.append({
            "path": normalized,
            "declared_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "declared_bytes": int(expected_size),
            "actual_bytes": actual_size,
            "hash_match": actual_hash == expected_hash,
            "size_match": actual_size == int(expected_size),
        })
    actual_payload = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    if actual_payload != seen:
        raise RuntimeError(json.dumps({
            "undeclared": sorted(actual_payload - seen),
            "declared_missing": sorted(seen - actual_payload),
        }))
    if any(not item["hash_match"] or not item["size_match"] for item in entries):
        raise RuntimeError("custom ledger content mismatch")
    return entries


def main():
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite existing inventory: {OUTPUT}")

    ingestion = json.loads(INGESTION.read_text())
    ledger_entries = parse_custom_ledger()

    report_path = ROOT / "MONICA-001-REPORT.json"
    report = json.loads(report_path.read_text())
    review_path = ROOT / "MONICA-001-REVIEW.md"
    if not review_path.read_text().startswith("# SOFA-HOT-008 / MONICA-001"):
        raise RuntimeError("unexpected review header")

    record_results = []
    json_validation = [file_identity(report_path, ROOT)]
    ast_validation = []
    for path in sorted((ROOT / "tests").glob("*.py")) + [ROOT / "build_reports.py"]:
        ast.parse(path.read_text(), filename=str(path))
        ast_validation.append(file_identity(path, ROOT))

    ranked_by_id = {item["case_id"]: item for item in report["cases_ranked"]}
    for prefix, case_id in EXPECTED_CASES.items():
        record_path = next((ROOT / "records").glob(prefix + "_*.json"))
        stderr_path = record_path.with_suffix(".stderr")
        exitcode_path = record_path.with_suffix(".exitcode")
        test_path = next((ROOT / "tests").glob(prefix + "_*.py"))
        record = json.loads(record_path.read_text())
        json_validation.append(file_identity(record_path, ROOT))
        exit_text = exitcode_path.read_text()
        ranked = ranked_by_id.get(case_id)
        checks = {
            "record_case_id_matches": record.get("case_id") == case_id,
            "exitcode_exact_zero": exit_text == "0",
            "stderr_empty": stderr_path.stat().st_size == 0,
            "report_case_present": ranked is not None,
            "report_exit_zero": ranked is not None and ranked.get("exit_code") == 0,
            "assertion_count_matches_report": ranked is not None and ranked.get("assertions") == record.get("assertions"),
            "test_source_matches_report": ranked is not None and ranked.get("test_source") == test_path.relative_to(ROOT).as_posix(),
            "machine_record_matches_report": ranked is not None and ranked.get("machine_record") == record_path.relative_to(ROOT).as_posix(),
        }
        if not all(checks.values()):
            raise RuntimeError(f"record/report validation failed for {prefix}: {checks}")
        record_results.append({
            "case": prefix,
            "case_id": case_id,
            "test_source": file_identity(test_path, ROOT),
            "machine_record": file_identity(record_path, ROOT),
            "stderr": file_identity(stderr_path, ROOT),
            "exitcode": file_identity(exitcode_path, ROOT),
            "exitcode_value": 0,
            "assertions": record.get("assertions"),
            "execution_claim": record.get("execution"),
            "checks": checks,
            "record": record,
        })

    raw_sources = sorted((ROOT / "sources").glob("*"))
    supplied_source_case_ids = {
        "02c83759-175f-4e00-8b7b-8962f3ba33c4",
        "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
    }
    source_status = {
        case_id: ("SUPPLIED" if case_id in supplied_source_case_ids else "NOT_SUPPLIED")
        for case_id in EXPECTED_CASES.values()
    }

    environment_lines = (ROOT / "environment.txt").read_text().splitlines()
    archive_after_full_verification = {
        "bytes": ARCHIVE.stat().st_size,
        "sha256": sha256(ARCHIVE),
        "mtime_ns": ARCHIVE.stat().st_mtime_ns,
        "mode": oct(ARCHIVE.stat().st_mode & 0o777),
    }
    archive_unchanged = (
        archive_after_full_verification["bytes"] == ingestion["archive_before"]["bytes"]
        and archive_after_full_verification["sha256"] == ingestion["archive_before"]["sha256"]
        and archive_after_full_verification["mtime_ns"] == ingestion["archive_before"]["mtime_ns"]
        and archive_after_full_verification["mode"] == ingestion["archive_before"]["mode"]
    )
    if not archive_unchanged:
        raise RuntimeError("archive changed after full verification")

    inventory = {
        "schema": "SOFA-HOT-008-MONICA-ARCHIVE-INVENTORY-v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": {
            "original_filename": ingestion["archive_before"]["path"],
            "bytes": ingestion["archive_before"]["bytes"],
            "sha256": ingestion["archive_before"]["sha256"],
            "kind": ingestion["archive_kind"],
            "gzip_integrity": ingestion["gzip_integrity"],
            "unchanged_before_after_ingestion": ingestion["archive_byte_identical_and_metadata_stable"],
            "unchanged_after_full_verification": archive_unchanged,
            "post_verification_identity": archive_after_full_verification,
        },
        "archive_safety": ingestion["safety_checks"],
        "limits": ingestion["limits"],
        "members": ingestion["members"],
        "extraction_decisions": ingestion["decisions"],
        "extracted_files": ingestion["extracted_files"],
        "extraction_root": ingestion["extraction_root"],
        "supplied_ledger": {
            "path": "SHA256SUMS.txt",
            "format": "sha256<two spaces>path<two spaces>byte_size",
            "gnu_sha256sum_c_compatible": False,
            "gnu_sha256sum_c_result": "PARSER_FAILURE_NOT_CONTENT_MISMATCH",
            "independent_parser_status": "PASS",
            "entry_count": len(ledger_entries),
            "covers_every_nonledger_file": True,
            "entries": ledger_entries,
        },
        "artifact_presence": {
            "test_sources": {"status": "SUPPLIED", "count": 8},
            "machine_records": {"status": "SUPPLIED", "count": 8},
            "exitcode_records": {"status": "SUPPLIED", "count": 8},
            "stderr_records": {"status": "SUPPLIED", "count": 8},
            "review": {"status": "SUPPLIED", **file_identity(review_path, ROOT)},
            "report": {"status": "SUPPLIED", **file_identity(report_path, ROOT)},
            "ledger": {"status": "SUPPLIED", **file_identity(ROOT / "SHA256SUMS.txt", ROOT)},
            "environment": {"status": "SUPPLIED", **file_identity(ROOT / "environment.txt", ROOT)},
            "raw_source_snapshots": {
                "status": "PARTIAL",
                "count": len(raw_sources),
                "files": [file_identity(path, ROOT) for path in raw_sources],
                "by_post_id": source_status,
            },
            "per_case_exact_argv": "NOT_SUPPLIED",
            "per_case_execution_timestamps": "NOT_SUPPLIED",
            "package_install_command_receipts": "NOT_SUPPLIED",
            "raw_stdout": "SUPPLIED_AS_RECORD_JSON",
        },
        "syntax_validation": {
            "json_status": "PASS",
            "json_files": json_validation,
            "python_ast_status": "PASS_SOURCE_INSPECTION_ONLY",
            "python_files": ast_validation,
            "archive_scripts_executed_by_custodian": False,
        },
        "execution_evidence": {
            "status": "SUPPORTED_BY_RECORD_EXITCODE_STDERR_TRIPLETS",
            "records": record_results,
            "provenance_limit": "No per-case execution timestamps or exact argv receipts were supplied; source existence alone was not used as execution proof.",
            "all_exitcodes_zero": True,
            "all_stderr_empty": True,
            "report_generic_command": report.get("commands"),
        },
        "environment": {
            "raw_lines": environment_lines,
            "package_versions": report.get("package_versions"),
            "declared_execution_platform": "virtual_machine_not_native_physical_workstation",
        },
        "protocol_deviations": [
            {
                "item": "deterministic_seed",
                "required": 26051108,
                "reported_by_monica": report.get("independence", {}).get("seed"),
                "impact": "Case 07 randomized shuffle used a different seed; deterministic, but not the protocol-mandated seed.",
            }
        ],
        "source_evidence_limit": "Only Cases 02 and 03 include raw HTML snapshots. Reply-count/current-content claims for the other six cannot be reconstructed from the archive alone.",
        "integrity_verdict": "PASS_WITH_NONSTANDARD_LEDGER_FORMAT",
        "missing_artifacts": [
            "NOT_SUPPLIED: raw source snapshots for Cases 01 and 04-08",
            "NOT_SUPPLIED: per-case exact argv and execution timestamps",
            "NOT_SUPPLIED: package installation/version command receipts",
            "NOT_SUPPLIED: mypy and Pyright execution",
            "NOT_SUPPLIED: real yt-dlp extraction, Excel rendering, Discord, or SPN2 observations",
        ],
    }
    OUTPUT.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(OUTPUT),
        "bytes": OUTPUT.stat().st_size,
        "sha256": sha256(OUTPUT),
        "integrity_verdict": inventory["integrity_verdict"],
        "ledger_entries": len(ledger_entries),
        "records": len(record_results),
        "archive_unchanged": archive_unchanged,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
