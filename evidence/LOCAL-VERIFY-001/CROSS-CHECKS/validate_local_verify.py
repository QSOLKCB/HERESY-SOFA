#!/usr/bin/env python3
"""Standard-library integrity and regression checks for LOCAL-VERIFY-001."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: str) -> object:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class LocalVerifyEvidenceTests(unittest.TestCase):
    maxDiff = None

    def test_required_directories_and_files(self) -> None:
        for directory in ("PYTHON-TYPING", "SPN2-SCHEDULER", "CROSS-CHECKS", "RECEIPTS", "REPORTS"):
            self.assertTrue((ROOT / directory).is_dir(), directory)
        for path in (
            "REPORTS/LOCAL-VERIFY-001-ENVIRONMENT.json",
            "REPORTS/LOCAL-VERIFY-001-TEST-MATRIX.csv",
            "REPORTS/LOCAL-VERIFY-001-REPORT.json",
            "REPORTS/LOCAL-VERIFY-001-REVIEW.md",
            "REPORTS/LOCAL-VERIFY-001-CLAIM-LEDGER.csv",
            "REPORTS/LOCAL-VERIFY-001-OPEN-ISSUES.md",
            "RECEIPTS/LOCAL-VERIFY-001-EXECUTION.json",
            "PYTHON-TYPING/runtime-result.json",
            "SPN2-SCHEDULER/scheduler-result.json",
        ):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_no_symlinks_or_generated_caches(self) -> None:
        for path in ROOT.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            self.assertNotIn(path.name, {"__pycache__", ".mypy_cache"})

    def test_environment_and_historical_boundary(self) -> None:
        env = load("REPORTS/LOCAL-VERIFY-001-ENVIRONMENT.json")
        self.assertEqual(env["operating_system"]["os_release"]["PRETTY_NAME"], "Ubuntu 26.04.1 LTS")
        self.assertEqual(env["operating_system"]["kernel_release"], "7.0.0-42-generic")
        self.assertEqual(env["operating_system"]["architecture"], "x86_64")
        self.assertEqual(env["python"]["version"], "3.14.4")
        self.assertTrue(env["repository"]["pr16_is_ancestor_of_origin_main"])
        self.assertTrue(env["repository"]["pr17_is_ancestor_of_origin_main"])
        baseline = load("CROSS-CHECKS/historical-baseline.json")
        self.assertEqual(baseline["origin_main"], "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a")
        self.assertEqual(
            baseline["frozen_historical_evidence"]["codex_primary_report"]["sha256"],
            "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229",
        )
        self.assertEqual(
            baseline["frozen_historical_evidence"]["monica_archive"]["sha256"],
            "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202",
        )

    def test_execution_receipt(self) -> None:
        receipt = load("RECEIPTS/LOCAL-VERIFY-001-EXECUTION.json")
        self.assertEqual(receipt["total_runtime_assertion_count"], 59)
        self.assertEqual(receipt["total_runtime_negative_control_count"], 20)
        self.assertEqual(receipt["failed_check_count"], 0)
        self.assertEqual(receipt["check_count"], 20)
        self.assertEqual(len(receipt["commands"]), 10)
        self.assertTrue(receipt["source_inventory_before_and_after_identical"])
        for output in receipt["outputs"]:
            path = ROOT / output["path"]
            self.assertEqual(path.stat().st_size, output["bytes"], path)
            self.assertEqual(sha256(path), output["sha256"], path)
        for source in receipt["sources"]:
            path = ROOT / source["path"]
            self.assertEqual(path.stat().st_size, source["bytes"], path)
            self.assertEqual(sha256(path), source["sha256"], path)

    def test_native_runtime_results(self) -> None:
        result = load("PYTHON-TYPING/runtime-result.json")
        self.assertEqual(result["assertion_count"], 18)
        self.assertEqual(result["negative_control_count"], 7)
        self.assertEqual(result["failed_assertion_count"], 0)
        self.assertEqual(
            result["observations"]["posted_dataclass_defaults"],
            {"myclass[C]": "C", "myclass[C2]": "C", "myclass_child": "C2"},
        )
        self.assertEqual(
            result["observations"]["typevartuple_runtime_forms"]["literal_ellipsis"]["args_repr"],
            ["<class 'int'>", "Ellipsis"],
        )
        error = (ROOT / "PYTHON-TYPING/generic-alias-verbatim.stderr.txt").read_text(encoding="utf-8")
        self.assertIn("TypeError: type 'types.GenericAlias' is not subscriptable", error)

    def test_checker_coverage_is_version_scoped(self) -> None:
        inventory = load("CROSS-CHECKS/checker-inventory.json")
        self.assertEqual(inventory["executables"]["mypy"], "/usr/bin/mypy")
        self.assertIsNone(inventory["executables"]["pyright"])
        self.assertIsNone(inventory["executables"]["basedpyright"])
        self.assertEqual(inventory["bounded_cache_search"]["matches"], [])
        self.assertEqual(inventory["coverage"]["mypy_2.3.1"], "NOT_TESTED")
        self.assertEqual(inventory["coverage"]["pyright_1.1.414"], "NOT_TESTED")
        self.assertIn(
            'Unexpected "..."  [misc]',
            (ROOT / "PYTHON-TYPING/A4-genericalias-negative.txt").read_text(encoding="utf-8"),
        )

    def test_scheduler_results_and_oracle(self) -> None:
        result = load("SPN2-SCHEDULER/scheduler-result.json")
        self.assertEqual(result["assertion_count"], 41)
        self.assertEqual(result["negative_control_count"], 13)
        self.assertEqual(result["failed_assertion_count"], 0)
        self.assertFalse(result["network_access"])
        broken = result["scenarios"]["C1_broken_posted_loop"]
        self.assertEqual((broken["submission_attempts"], broken["polling_attempts"]), (4, 0))
        self.assertEqual(
            (broken["minimum_counterexample"]["submission_attempts"], broken["minimum_counterexample"]["polling_attempts"]),
            (2, 0),
        )
        agreement = result["scenarios"]["C2_fair_scheduler_and_oracle"]["oracle"]["agreement"]
        self.assertTrue(all(agreement.values()))
        self.assertEqual(
            set(result["represented_states"]),
            {
                "QUEUED", "SUBMITTING", "ACCEPTED", "PENDING",
                "SUCCEEDED_UNVERIFIED", "VERIFIED", "FAILED_RETRYABLE",
                "FAILED_PERMANENT", "UNCERTAIN_ACCEPTANCE",
            },
        )

    def test_matrix_and_claim_ledger(self) -> None:
        with (ROOT / "REPORTS/LOCAL-VERIFY-001-TEST-MATRIX.csv").open(newline="", encoding="utf-8") as stream:
            matrix = list(csv.DictReader(stream))
        self.assertEqual(len(matrix), 40)
        self.assertEqual(sum(row["pass_fail"] == "NOT_TESTED" for row in matrix), 2)
        self.assertTrue(all(row["evidence_class"] in {
            "EXECUTED_NATIVE", "EXECUTED_SIMULATED", "DOCUMENTATION_VERIFIED",
            "INFERRED", "NOT_TESTED", "CONTRADICTED",
        } for row in matrix))
        with (ROOT / "REPORTS/LOCAL-VERIFY-001-CLAIM-LEDGER.csv").open(newline="", encoding="utf-8") as stream:
            claims = list(csv.DictReader(stream))
        self.assertEqual(len(claims), 14)
        self.assertEqual({row["case_id"] for row in claims}, {"03", "06", "08"})

    def test_current_sofa_source_identity(self) -> None:
        snapshot = load("CROSS-CHECKS/current-sofa-source-snapshot.json")
        expected = {
            "0b3591f6-75de-4661-a7a7-ec28193e1518": "10ee7651a8ae6bb9cd9fc8293788615e286c55021f5a115f08719d52764f8e7d",
            "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7": "cc42b362476c672a7e17faf7b073f16c3f570c642a8a117ef87c24475be07e40",
            "da4cf061-dba9-4c01-b42c-f94e6f3b6279": "a823d4940b574c856985e89f40714b1ef47b2a7880f5c57a6468c2689cb3a3e1",
        }
        actual = {}
        for entry in snapshot["posts"]:
            post = entry["response"]["data"]
            actual[post["id"]] = hashlib.sha256(post["body"].encode("utf-8")).hexdigest()
        self.assertEqual(actual, expected)

    def test_sha256_manifest_when_present(self) -> None:
        ledger = ROOT / "SHA256SUMS.txt"
        if not ledger.exists():
            self.skipTest("manifest is created only at finalization")
        covered: set[str] = set()
        for line in ledger.read_text(encoding="utf-8").splitlines():
            digest, marker, relative = line.partition("  ")
            self.assertEqual(marker, "  ")
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(sha256(path), digest, relative)
            covered.add(relative)
        expected = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path != ledger
        }
        self.assertEqual(covered, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
