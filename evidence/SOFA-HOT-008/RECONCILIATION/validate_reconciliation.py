#!/usr/bin/env python3
"""Validate the finalized reconciliation package without executing witness code."""

import csv
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/trent/SOFA-HOT-008/RECONCILIATION")
WORKSPACE = ROOT.parent
OUTPUT = ROOT / "RECONCILIATION-VALIDATION.json"
SIGNATURE = "More edge case Gremlins for the Goblin God!"
POST_IDS = {
    "01": "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
    "02": "02c83759-175f-4e00-8b7b-8962f3ba33c4",
    "03": "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
    "04": "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
    "05": "47de513f-cd52-4b36-a43d-ec4cb89c972f",
    "06": "0b3591f6-75de-4661-a7a7-ec28193e1518",
    "07": "4a28aa43-10aa-4476-b33b-85cc91998975",
    "08": "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
}
CASE_CLASSIFICATIONS = {
    "01": "INSUFFICIENT_EVIDENCE",
    "02": "CONFIRMED_BY_BOTH",
    "03": "CONFIRMED_BY_BOTH",
    "04": "CONFIRMED_BY_ONE",
    "05": "INSUFFICIENT_EVIDENCE",
    "06": "CONFIRMED_BY_ONE",
    "07": "CONFIRMED_BY_BOTH",
    "08": "CONFIRMED_BY_ONE",
}
ACTIONS = {
    "01": "NEEDS_MORE_EVIDENCE",
    "02": "NO_ACTION",
    "03": "REPLY",
    "04": "REPLY",
    "05": "REPLY",
    "06": "REPLY",
    "07": "NO_ACTION",
    "08": "REPLY",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def identity(path: Path) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT) else str(path),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


class Validator:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def check(self, name: str, condition: bool, observed=None) -> None:
        record = {"name": name, "passed": bool(condition)}
        if observed is not None:
            record["observed"] = observed
        self.checks.append(record)
        if not condition:
            raise AssertionError(f"validation failed: {name}: {observed!r}")


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite {OUTPUT}")

    validator = Validator()
    required = [
        ROOT / "CODEX-BASELINE.json",
        ROOT / "MONICA-ARCHIVE-INVENTORY.json",
        ROOT / "MONICA-INGESTION-RECEIPT.json",
        ROOT / "SOFA-CURRENT-SNAPSHOT.json",
        ROOT / "SOFA-CONNECTION-STATUS.json",
        ROOT / "SOFA-ACTIVITY-RECONCILIATION.json",
        ROOT / "SOFA-HOT-008-CLAIM-LEDGER.csv",
        ROOT / "SOFA-HOT-008-DUAL-WITNESS-REPORT.json",
        ROOT / "SOFA-HOT-008-DUAL-WITNESS-REVIEW.md",
        ROOT / "SOFA-HOT-008-PUBLICATION-LEDGER.json",
        ROOT / "SOFA-SESSION-SUMMARY.json",
        ROOT / "RECONCILIATION-COMMAND-LOG.json",
        ROOT / "SOFA-DRAFTS" / "INDEX.json",
        ROOT / "CODEX-RECONCILIATION-TESTS" / "CASE-06" / "receipt.json",
    ]
    validator.check("required_artifacts_present", all(path.is_file() for path in required),
                    [path.name for path in required if not path.is_file()])

    baseline = json.loads((ROOT / "CODEX-BASELINE.json").read_text())
    monica = json.loads((ROOT / "MONICA-ARCHIVE-INVENTORY.json").read_text())
    snapshot = json.loads((ROOT / "SOFA-CURRENT-SNAPSHOT.json").read_text())
    report = json.loads((ROOT / "SOFA-HOT-008-DUAL-WITNESS-REPORT.json").read_text())
    publication = json.loads((ROOT / "SOFA-HOT-008-PUBLICATION-LEDGER.json").read_text())
    draft_index = json.loads((ROOT / "SOFA-DRAFTS" / "INDEX.json").read_text())
    followup = json.loads((ROOT / "CODEX-RECONCILIATION-TESTS" / "CASE-06" / "receipt.json").read_text())
    session = json.loads((ROOT / "SOFA-SESSION-SUMMARY.json").read_text())
    connection = json.loads((ROOT / "SOFA-CONNECTION-STATUS.json").read_text())
    activity = json.loads((ROOT / "SOFA-ACTIVITY-RECONCILIATION.json").read_text())

    primary_root = Path(baseline["primary"]["root"])
    alternate_root = Path(baseline["alternate_codex_package"]["root"])
    for label, root, record in (
        ("primary", primary_root, baseline["primary"]),
        ("auxiliary", alternate_root, baseline["alternate_codex_package"]),
    ):
        actual_report = root / record["report"]["path"]
        actual_ledger = root / record["ledger"]["path"]
        validator.check(f"codex_{label}_report_identity",
                        actual_report.stat().st_size == record["report"]["bytes"]
                        and digest(actual_report) == record["report"]["sha256"],
                        identity(actual_report))
        validator.check(f"codex_{label}_ledger_identity",
                        actual_ledger.stat().st_size == record["ledger"]["bytes"]
                        and digest(actual_ledger) == record["ledger"]["sha256"],
                        identity(actual_ledger))
        validator.check(f"codex_{label}_ledger_recorded_pass",
                        record["ledger_verification"] == "PASS",
                        record["ledger_verification"])
    validator.check("codex_primary_receipts_zero",
                    baseline["primary"]["all_final_receipts_exit_zero"] is True
                    and baseline["primary"]["all_final_receipts_have_no_failed_checks"] is True)
    validator.check("baseline_precedes_monica_inspection",
                    baseline["baseline_status"] == "FROZEN_BEFORE_MONICA_INSPECTION"
                    and baseline["independence_boundary"]["monica_findings_read_before_this_record"] is False,
                    baseline["baseline_status"])

    archive = WORKSPACE / monica["archive"]["original_filename"]
    archive_stat = archive.stat()
    recorded_archive = monica["archive"]["post_verification_identity"]
    validator.check("monica_archive_byte_identity",
                    archive_stat.st_size == recorded_archive["bytes"]
                    and archive_stat.st_mtime_ns == recorded_archive["mtime_ns"]
                    and stat.S_IMODE(archive_stat.st_mode) == int(recorded_archive["mode"], 8)
                    and digest(archive) == recorded_archive["sha256"],
                    {"bytes": archive_stat.st_size, "mtime_ns": archive_stat.st_mtime_ns,
                     "mode": oct(stat.S_IMODE(archive_stat.st_mode)), "sha256": digest(archive)})
    validator.check("monica_integrity_verdict",
                    monica["integrity_verdict"] == "PASS_WITH_NONSTANDARD_LEDGER_FORMAT",
                    monica["integrity_verdict"])
    validator.check("monica_archive_member_safety",
                    monica["archive_safety"]["regular_file_count"] == 39
                    and monica["archive_safety"]["member_count"] == 43
                    and all(str(value).startswith("PASS")
                            for key, value in monica["archive_safety"].items()
                            if key in {"absolute_paths", "dotdot_traversal", "duplicate_normalized_paths",
                                       "devices", "fifos", "hardlinks", "symlinks", "unexpected_types"}),
                    monica["archive_safety"])

    extraction_root = ROOT / "MONICA-EXTRACTED-cc3d4ae960c6"
    extracted_mismatches = []
    for record in monica["extracted_files"]:
        path = extraction_root / record["relative_path"]
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != record["bytes"]
                or digest(path) != record["sha256"]):
            extracted_mismatches.append(record["relative_path"])
    validator.check("monica_extracted_files_match_inventory",
                    not extracted_mismatches and len(monica["extracted_files"]) == 39,
                    extracted_mismatches)

    posts = {post["id"]: post for post in snapshot["posts"]}
    validator.check("sofa_snapshot_eight_sources", set(posts) == set(POST_IDS.values()), sorted(posts))
    validator.check("sofa_reply_counts_consistent",
                    all(post["reply_count"] == len(post.get("replies", [])) for post in posts.values()))

    with (ROOT / "SOFA-HOT-008-CLAIM-LEDGER.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        claim_rows = list(reader)
        claim_fields = reader.fieldnames or []
    validator.check("claim_ledger_schema",
                    len(claim_rows) == 37
                    and {row["Case ID"] for row in claim_rows} == set(POST_IDS)
                    and {"Original author", "Original body SHA-256", "Current reply identities",
                         "Codex evidence kind", "Monica evidence kind", "Reconciliation status"}
                    <= set(claim_fields),
                    {"rows": len(claim_rows), "fields": claim_fields})
    validator.check("claim_ledger_source_attribution",
                    all(row["Original post ID"] == POST_IDS[row["Case ID"]]
                        and row["Original author"] == posts[row["Original post ID"]]["agent_name"]
                        and row["Original body SHA-256"] == digest_text(posts[row["Original post ID"]]["body"])
                        for row in claim_rows))
    allowed_claim_statuses = {
        "CONFIRMED_BY_BOTH", "CONFIRMED_BY_ONE", "CONTRADICTED",
        "INSUFFICIENT_EVIDENCE", "NO_DEFECT",
    }
    validator.check("claim_status_vocabulary",
                    {row["Reconciliation status"] for row in claim_rows} <= allowed_claim_statuses,
                    sorted({row["Reconciliation status"] for row in claim_rows}))
    validator.check("observed_vs_inferred_columns_populated",
                    all(row["Codex evidence kind"] and row["Monica evidence kind"]
                        and row["Known limitations"] for row in claim_rows))

    cases = {case["case"]: case for case in report["cases"]}
    validator.check("eight_case_classifications",
                    {case: value["classification"] for case, value in cases.items()} == CASE_CLASSIFICATIONS,
                    {case: value["classification"] for case, value in cases.items()})
    validator.check("eight_case_publication_actions",
                    {case: value["publication_action"] for case, value in cases.items()} == ACTIONS,
                    {case: value["publication_action"] for case, value in cases.items()})
    validator.check("report_claim_ledger_identity",
                    report["claim_ledger"] == identity(ROOT / "SOFA-HOT-008-CLAIM-LEDGER.csv"),
                    report["claim_ledger"])
    validator.check("report_source_identities",
                    all(case["source_identity"]["original_author"] == posts[case["post_id"]]["agent_name"]
                        and case["source_identity"]["body_sha256"] == digest_text(posts[case["post_id"]]["body"])
                        and len(case["source_identity"]["replies"]) == len(posts[case["post_id"]].get("replies", []))
                        for case in cases.values()))

    draft_cases = {draft["case"]: draft for draft in draft_index["drafts"]}
    validator.check("draft_cases_exact", set(draft_cases) == {"03", "04", "05", "06", "08"}, sorted(draft_cases))
    for case, record in draft_cases.items():
        path = ROOT / record["path"]
        body = path.read_text()
        validator.check(f"draft_{case}_identity",
                        path.stat().st_size == record["bytes"] and digest(path) == record["sha256"],
                        identity(path))
        validator.check(f"draft_{case}_exact_signature",
                        body.endswith(SIGNATURE + "\n")
                        and not body.endswith(SIGNATURE + "\n\n"), body.splitlines()[-1])
        validator.check(f"draft_{case}_no_outbound_url",
                        re.search(r"https?://|www\.|\]\(\s*https?://", body, re.I) is None)
        validator.check(f"draft_{case}_no_private_machine_detail",
                        re.search(r"/home/|ubuntu|cloudflare-microvm|ryzen|epyc", body, re.I) is None)

    publication_cases = {case["case"]: case for case in publication["cases"]}
    validator.check("publication_gate_closed",
                    publication["authorization_gate"] == "CLOSED_AWAITING_OWNER_APPROVAL_OF_SPECIFIC_DRAFTS"
                    and publication["writes_attempted"] == 0
                    and publication["writes_attempted_scope"] == "this SOFA-HOT-008 reconciliation only"
                    and publication["publication_events"] == [])
    validator.check("publication_connection_status_current_receipt",
                    publication["connection_snapshot"]["connection_id"] == connection["data"]["connection_id"]
                    and publication["connection_snapshot"]["agent_id"] == connection["data"]["agent_id"]
                    and publication["connection_snapshot"]["selected_agent"] == connection["data"]["agent_name"]
                    and publication["connection_snapshot"]["capabilities_at_status_check"] == connection["data"]["scopes"]
                    and publication["connection_snapshot"]["latest_status_receipt"] == identity(ROOT / "SOFA-CONNECTION-STATUS.json"))
    validator.check("publication_activity_reconciliation_receipt",
                    {key: publication["activity_reconciliation"][key]
                     for key in ("path", "bytes", "sha256")} == identity(ROOT / "SOFA-ACTIVITY-RECONCILIATION.json")
                    and publication["activity_reconciliation"]["status"] == activity["conclusion"]["status"])
    validator.check("publication_states_not_attempted",
                    all(item["action"] == ACTIONS[case]
                        and item["publication"]["state"] == "NOT_ATTEMPTED"
                        and item["publication"]["reply_id"] is None
                        and item["publication"]["lifecycle_state"] is None
                        for case, item in publication_cases.items()))
    validator.check("initial_sofa_session_receipt_preserved_with_warning",
                    session["data"]["contribution_count"] == 0
                    and activity["initial_session_receipt"]["session_id"] == session["data"]["session_id"]
                    and bool(activity["initial_session_receipt"]["warning"]),
                    session["data"])
    target_readback = {item["post_id"]: item for item in activity["target_readback"]}
    validator.check("late_target_readback_matches_frozen_snapshot",
                    set(target_readback) == set(posts)
                    and all(target_readback[post_id]["reply_count"] == post["reply_count"]
                            and target_readback[post_id]["reply_ids"] == [reply["id"] for reply in post.get("replies", [])]
                            and target_readback[post_id]["updated_at"] == post["updated_at"]
                            for post_id, post in posts.items()))
    validator.check("concurrent_agent_activity_outside_target_scope",
                    len(activity["recent_authenticated_agent_contributions"]) == 2
                    and all(item["target_post_match"] is False
                            and item["parent_id"] not in posts
                            for item in activity["recent_authenticated_agent_contributions"])
                    and activity["conclusion"]["write_tool_calls_in_this_reconciliation"] == 0
                    and activity["conclusion"]["eight_target_posts_unchanged_from_2026-11-04T17:02:54.572Z_snapshot"] is True,
                    activity["recent_authenticated_agent_contributions"])
    validator.check("report_sofa_receipts",
                    report["current_sofa_connection_status"] == identity(ROOT / "SOFA-CONNECTION-STATUS.json")
                    and {key: report["initial_sofa_session_summary"][key]
                         for key in ("path", "bytes", "sha256")} == identity(ROOT / "SOFA-SESSION-SUMMARY.json")
                    and report["sofa_activity_reconciliation"] == identity(ROOT / "SOFA-ACTIVITY-RECONCILIATION.json"))
    validator.check("report_command_log_receipt",
                    report["reconciliation_command_log"] == identity(ROOT / "RECONCILIATION-COMMAND-LOG.json"))
    validator.check("followup_separate_and_passed",
                    followup["experiment_id"] == "CODEX-RECONCILIATION-TEST-CASE-06-TYPEVARTUPLE"
                    and followup["status"] == "PASS"
                    and followup["process_exit_code"] == 0
                    and followup["scope"] == "CPython runtime only; no Pyright inference"
                    and all(check["passed"] for check in followup["checks"]),
                    {"id": followup["experiment_id"], "status": followup["status"]})

    top_level_identities = {
        path.relative_to(ROOT).as_posix(): identity(path)
        for path in required
    }
    receipt = {
        "schema": "SOFA-HOT-008-RECONCILIATION-VALIDATION-v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python RECONCILIATION/validate_reconciliation.py",
        "process_exit_code": 0,
        "status": "PASS",
        "checks_passed": len(validator.checks),
        "checks_failed": 0,
        "checks": validator.checks,
        "required_artifact_identities": top_level_identities,
        "monica_archive_after_reconciliation": {
            "path": monica["archive"]["original_filename"],
            "bytes": archive_stat.st_size,
            "sha256": digest(archive),
            "unchanged": True,
        },
        "publication": {
            "authorized": False,
            "writes_attempted": 0,
            "writes_attempted_scope": "this reconciliation",
            "initial_session_contribution_count": 0,
            "late_same_session_contribution_count": 2,
            "session_isolation": "UNAVAILABLE",
            "eight_target_posts_unchanged": True,
        },
        "note": "Validation reads evidence only and does not execute any extracted Monica script.",
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "PASS",
        "checks": len(validator.checks),
        "receipt": identity(OUTPUT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
