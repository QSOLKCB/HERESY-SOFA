"""Integrity and result-boundary tests for LOCAL-VERIFY-001."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
ROOT = REPOSITORY / "evidence" / "LOCAL-VERIFY-001"
ARCHIVE = json.loads((ROOT / "ARCHIVE.json").read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


class LocalVerify001Tests(unittest.TestCase):
    maxDiff = None

    def test_archive_manifest_covers_payload(self) -> None:
        expected = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path not in {ROOT / "ARCHIVE.json", ROOT / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in ARCHIVE["files"]}
        self.assertEqual(ARCHIVE["campaign"], "LOCAL-VERIFY-001")
        self.assertEqual(ARCHIVE["repository_base_commit"], "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a")
        self.assertEqual(set(records), expected)
        self.assertEqual(ARCHIVE["file_count_excluding_metadata"], len(records))
        for relative, record in records.items():
            data = (ROOT / relative).read_bytes()
            self.assertEqual(len(data), record["bytes"], relative)
            self.assertEqual(sha256(data), record["sha256"], relative)
            self.assertEqual(git_blob(data), record["git_blob_sha"], relative)

    def test_sha256_ledger_covers_every_file_except_itself(self) -> None:
        ledger = {}
        for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            value, relative = line.split("  ", 1)
            self.assertNotIn(relative, ledger)
            ledger[relative] = value
        expected = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path != ROOT / "SHA256SUMS.txt"
        }
        self.assertEqual(set(ledger), expected)
        for relative, value in ledger.items():
            self.assertEqual(sha256((ROOT / relative).read_bytes()), value, relative)

    def test_historical_boundary_and_witness_identities(self) -> None:
        baseline = json.loads((ROOT / "CROSS-CHECKS/historical-baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(baseline["origin_main"], "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a")
        self.assertTrue(baseline["required_merges"]["pr_16"]["ancestor_of_origin_main"])
        self.assertTrue(baseline["required_merges"]["pr_17"]["ancestor_of_origin_main"])
        self.assertEqual(
            baseline["frozen_historical_evidence"]["codex_primary_report"]["sha256"],
            "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229",
        )
        self.assertEqual(
            baseline["frozen_historical_evidence"]["monica_archive"]["sha256"],
            "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202",
        )

    def test_execution_receipt_and_determinism(self) -> None:
        receipt = json.loads((ROOT / "RECEIPTS/LOCAL-VERIFY-001-EXECUTION.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["total_runtime_assertion_count"], 59)
        self.assertEqual(receipt["total_runtime_negative_control_count"], 20)
        self.assertEqual(receipt["failed_check_count"], 0)
        self.assertEqual(len(receipt["commands"]), 10)
        self.assertTrue(receipt["source_inventory_before_and_after_identical"])
        determinism = json.loads((ROOT / "CROSS-CHECKS/determinism.json").read_text(encoding="utf-8"))
        self.assertTrue(determinism["source_unchanged"])
        self.assertTrue(all(
            result["byte_identical"]
            for result in determinism["fresh_process_pairs"].values()
        ))

    def test_generic_alias_and_dataclass_observations(self) -> None:
        runtime = json.loads((ROOT / "PYTHON-TYPING/runtime-result.json").read_text(encoding="utf-8"))
        self.assertEqual(runtime["failed_assertion_count"], 0)
        self.assertEqual(runtime["assertion_count"], 18)
        self.assertEqual(
            runtime["observations"]["posted_dataclass_defaults"],
            {"myclass[C]": "C", "myclass[C2]": "C", "myclass_child": "C2"},
        )
        self.assertEqual(
            runtime["observations"]["typevartuple_runtime_forms"]["literal_ellipsis"]["args_repr"],
            ["<class 'int'>", "Ellipsis"],
        )
        stderr = (ROOT / "PYTHON-TYPING/generic-alias-verbatim.stderr.txt").read_text(encoding="utf-8")
        self.assertIn("TypeError: type 'types.GenericAlias' is not subscriptable", stderr)

    def test_checker_scope_is_not_overstated(self) -> None:
        inventory = json.loads((ROOT / "CROSS-CHECKS/checker-inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(inventory["coverage"]["mypy_1.19.1"], "EXECUTED_NATIVE")
        self.assertEqual(inventory["coverage"]["mypy_2.3.1"], "NOT_TESTED")
        self.assertEqual(inventory["coverage"]["pyright_1.1.414"], "NOT_TESTED")
        self.assertIsNone(inventory["executables"]["pyright"])
        self.assertEqual(inventory["bounded_cache_search"]["matches"], [])

    def test_scheduler_failure_and_reference_oracle(self) -> None:
        result = json.loads((ROOT / "SPN2-SCHEDULER/scheduler-result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["assertion_count"], 41)
        self.assertEqual(result["failed_assertion_count"], 0)
        self.assertFalse(result["network_access"])
        broken = result["scenarios"]["C1_broken_posted_loop"]
        self.assertEqual((broken["submission_attempts"], broken["polling_attempts"]), (4, 0))
        minimum = broken["minimum_counterexample"]
        self.assertEqual((minimum["submission_attempts"], minimum["polling_attempts"]), (2, 0))
        agreement = result["scenarios"]["C2_fair_scheduler_and_oracle"]["oracle"]["agreement"]
        self.assertTrue(all(agreement.values()))
        self.assertEqual(
            result["scenarios"]["C3_lost_acceptance"]["unresolved_control"]["tasks"]["unresolved"]["state"],
            "UNCERTAIN_ACCEPTANCE",
        )
        self.assertEqual(
            result["scenarios"]["C5_capture_verification"]["index_absent"]["tasks"]["absent"]["state"],
            "SUCCEEDED_UNVERIFIED",
        )

    def test_reports_preserve_evidence_classes(self) -> None:
        with (ROOT / "REPORTS/LOCAL-VERIFY-001-TEST-MATRIX.csv").open(newline="", encoding="utf-8") as stream:
            matrix = list(csv.DictReader(stream))
        self.assertEqual(len(matrix), 40)
        self.assertEqual(sum(item["pass_fail"] == "NOT_TESTED" for item in matrix), 2)
        self.assertTrue(all(item["evidence_class"] in {
            "EXECUTED_NATIVE", "EXECUTED_SIMULATED", "DOCUMENTATION_VERIFIED",
            "INFERRED", "NOT_TESTED", "CONTRADICTED",
        } for item in matrix))
        report = json.loads((ROOT / "REPORTS/LOCAL-VERIFY-001-REPORT.json").read_text(encoding="utf-8"))
        self.assertEqual(report["results"]["A"]["classification"], "PARTIALLY_CORRECT")
        self.assertEqual(report["results"]["B"]["classification"], "CONFIRMED_DEFECT")
        self.assertEqual(report["results"]["C"]["classification"], "CONFIRMED_DEFECT")
        self.assertFalse(report["scope"]["network_service_tests"])
        self.assertFalse(report["scope"]["sofa_mutations"])

    def test_navigation_and_file_types(self) -> None:
        self.assertIn(
            "evidence/LOCAL-VERIFY-001/REPORTS/LOCAL-VERIFY-001-REVIEW.md",
            (REPOSITORY / "README.md").read_text(encoding="utf-8"),
        )
        self.assertFalse(any(path.is_symlink() for path in ROOT.rglob("*")))
        self.assertFalse(any(path.name in {"__pycache__", ".mypy_cache"} for path in ROOT.rglob("*")))


if __name__ == "__main__":
    unittest.main()
