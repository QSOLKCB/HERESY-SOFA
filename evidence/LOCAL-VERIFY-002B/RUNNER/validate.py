#!/usr/bin/env python3
"""Standard-library validation for the LOCAL-VERIFY-002B evidence archive."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
FROZEN = REPOSITORY / "evidence/LOCAL-VERIFY-002"
SOURCE_COMMIT = "1ad645e13277a28ba511cad2f6bd2f5d988894d8"


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalVerify002BTests(unittest.TestCase):
    maxDiff = None

    def test_required_artifacts_and_boundary(self) -> None:
        for relative in (
            "ENVIRONMENT.json", "PACKAGE-INVENTORY.json", "CHECKER-MATRIX.csv",
            "CLAIM-LEDGER.csv", "REPORT.json", "REVIEW.md", "NEGATIVE-CONTROLS.json",
            "OPEN-ISSUES.md", "BASELINE.json", "ARCHIVE.json", "SHA256SUMS.txt",
            "RAW/EXECUTION.json", "RAW/determinism.json", "RAW/package-inspection.json",
            "RAW/PREFLIGHT-PARSER-CORRECTION.json", "RAW/MYPY-DEPENDENCY-PREFLIGHT.json",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertFalse((REPOSITORY / "evidence/LOCAL-VERIFY-003").exists())
        self.assertFalse((REPOSITORY / "evidence/LOCAL-VERIFY-004").exists())

    def test_no_symlinks_or_generated_caches(self) -> None:
        for path in ROOT.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            self.assertNotIn(path.name, {"__pycache__", ".mypy_cache", ".pytest_cache"})

    def test_baseline_and_frozen_identity(self) -> None:
        baseline = load("BASELINE.json")
        self.assertEqual(baseline["source_commit"], SOURCE_COMMIT)
        self.assertEqual(baseline["pr_19"]["response"]["state"], "MERGED")
        self.assertEqual(
            baseline["pr_19"]["response"]["headRefOid"],
            "98054e2f4002b63bc724882bd6ee86f45f4fdb28",
        )
        self.assertFalse(baseline["historical_evidence_modified"])
        self.assertEqual(baseline["historical_diff_from_source_commit"], [])
        self.assertEqual(
            baseline["frozen_report"]["sha256"],
            "70f846f41b6d1da12c1e84b3de403ef631cf30dc8447b7a233cb284d758b5009",
        )
        self.assertEqual(sha256(FROZEN / "REPORT.json"), baseline["frozen_report"]["sha256"])
        self.assertEqual(sha256(FROZEN / "SHA256SUMS.txt"), baseline["frozen_manifest"]["sha256"])

    def test_environment_and_exact_versions(self) -> None:
        environment = load("ENVIRONMENT.json")
        self.assertEqual(environment["operating_system"]["os_release"]["PRETTY_NAME"], "Ubuntu 26.04.1 LTS")
        self.assertEqual(environment["operating_system"]["kernel_release"], "7.0.0-42-generic")
        self.assertEqual(environment["operating_system"]["architecture"], "x86_64")
        self.assertEqual(environment["tools"]["cpython"]["version"], "3.14.4")
        self.assertEqual(environment["tools"]["node"]["version"], "22.18.0")
        self.assertEqual(environment["tools"]["mypy"]["version"], "2.3.1")
        self.assertEqual(environment["tools"]["pyright"]["version"], "1.1.414")
        self.assertEqual(environment["tools"]["uv"]["version_output"], "uv 0.12.1 (x86_64-unknown-linux-gnu)")
        self.assertTrue(environment["mypy_environment"]["isolated_venv"])
        self.assertFalse(environment["mypy_environment"]["system_site_packages"])
        versions = {
            item["requested_name"]: item["version"]
            for item in environment["mypy_environment"]["distribution_inventory"]["distributions"]
        }
        self.assertEqual(versions, {
            "mypy": "2.3.1", "librt": "0.16.0", "ast-serialize": "0.13.1",
            "typing-extensions": "4.15.0", "mypy-extensions": "1.1.0", "pathspec": "1.0.4",
        })

    def test_package_inventory_and_archive_safety(self) -> None:
        inventory = load("PACKAGE-INVENTORY.json")
        inspection = load("RAW/package-inspection.json")
        self.assertEqual(inventory["artifact_count"], 7)
        self.assertTrue(inventory["original_archives_unchanged_after_inspection"])
        expected = {
            "mypy-2.3.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl": "8e036f06b41630f4c8a1d48f9ac6aa26acc65f8be089973f5519da643318f03f",
            "pyright-1.1.414.tgz": "bf5f473f6167c0d14175492c3263d783b4489a6956e1c06c18e15228e3a3fa42",
            "librt-0.16.0-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl": "ca8052401c55d7511dda6760719fda7618067e83535d7d0010096d216c34b667",
            "ast_serialize-0.13.1-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl": "9f99786e0d62082a5b121b3437f3167562133711df22128de1e9886f57f0b226",
            "typing_extensions-4.15.0-py3-none-any.whl": "f0fa19c6845758ab08074a0cfa8b7aecb71c999ca73d62883bc25cc018c4e548",
            "mypy_extensions-1.1.0-py3-none-any.whl": "1be4cccdb0f2482337c4743e60421de3a356cd97508abadd57d47403e94f5505",
            "pathspec-1.0.4-py3-none-any.whl": "fb6ae2fd4e7c921a165808a552060e722767cfa526f99ca5156ed2ce45a5c723",
        }
        self.assertEqual({item["filename"]: item["sha256"] for item in inventory["artifacts"]}, expected)
        for filename, digest in expected.items():
            self.assertEqual(sha256(ROOT / "PACKAGES" / filename), digest)
        self.assertEqual(inspection["decision"], "ACCEPTED")
        self.assertTrue(inspection["source_files_unchanged"])
        archive_items = [inspection["mypy"], inspection["pyright"], *inspection["mypy_dependencies"].values()]
        for item in archive_items:
            self.assertTrue(item["safety"]["accepted"])
            self.assertEqual(item["safety"]["duplicate_paths"], 0)
            self.assertEqual(item["safety"]["absolute_or_traversal_paths"], 0)
            self.assertEqual(item["safety"]["links_devices_fifos"], 0)

    def test_execution_and_determinism(self) -> None:
        execution = load("RAW/EXECUTION.json")
        self.assertEqual(execution["fixture_count"], 14)
        self.assertEqual(execution["matrix_rows"], 56)
        self.assertEqual(execution["mypy_matrix_rows"], 28)
        self.assertEqual(execution["pyright_matrix_rows"], 28)
        self.assertEqual(execution["fresh_process_checker_commands"], 112)
        self.assertEqual(execution["checker_timeouts"], [])
        self.assertEqual(execution["failed_negative_control_count"], 0)
        self.assertTrue(execution["source_unchanged"])
        self.assertFalse(execution["network_access_during_execution"])
        self.assertFalse(execution["package_manager_invocations_during_execution"])
        determinism = load("RAW/determinism.json")
        self.assertEqual(len(determinism["pairs"]), 56)
        self.assertTrue(determinism["all_semantic_repeat_pairs_identical"])
        self.assertTrue(all(item["semantic_output_identical"] for item in determinism["pairs"]))

    def test_checker_matrix_exact_coverage(self) -> None:
        matrix = rows("CHECKER-MATRIX.csv")
        self.assertEqual(len(matrix), 56)
        self.assertEqual(
            {(row["checker"], row["mode"]) for row in matrix},
            {("mypy", "default"), ("mypy", "strict"), ("Pyright", "standard"), ("Pyright", "strict")},
        )
        self.assertTrue(all(row["experiment_status"] == "PASS" for row in matrix))
        self.assertTrue(all(row["evidence_class"] == "CHECKER_CONFIRMED" for row in matrix))
        self.assertTrue(all(row["repeat_semantic_identical"] == "true" for row in matrix))
        self.assertTrue(all(
            row["result"] == "MATCHED_MYPY_1_19_1_EXIT"
            for row in matrix if row["checker"] == "mypy"
        ))

    def test_generic_alias_and_ellipsis_results(self) -> None:
        matrix = {(row["checker"], row["mode"], row["fixture_id"]): row for row in rows("CHECKER-MATRIX.csv")}
        for mode in ("default", "strict"):
            self.assertIn("attr-defined", matrix[("mypy", mode, "GA01")]["diagnostic_rules"])
            self.assertIn("operator", matrix[("mypy", mode, "GA02")]["diagnostic_rules"])
            self.assertIn("misc", matrix[("mypy", mode, "GA05")]["diagnostic_rules"])
            self.assertIn("type-arg", matrix[("mypy", mode, "GA06")]["diagnostic_rules"])
        for mode in ("standard", "strict"):
            self.assertIn("reportAttributeAccessIssue", matrix[("Pyright", mode, "GA01")]["diagnostic_rules"])
            self.assertIn("reportCallIssue", matrix[("Pyright", mode, "GA02")]["diagnostic_rules"])
            self.assertIn("reportInvalidTypeForm", matrix[("Pyright", mode, "GA05")]["diagnostic_rules"])
            self.assertIn("reportInvalidTypeArguments", matrix[("Pyright", mode, "GA06")]["diagnostic_rules"])

    def test_dataclass_results_and_checker_disagreement(self) -> None:
        matrix = {(row["checker"], row["mode"], row["fixture_id"]): row for row in rows("CHECKER-MATRIX.csv")}
        for mode in ("default", "strict"):
            self.assertIn("var-annotated", matrix[("mypy", mode, "DC01")]["diagnostic_rules"])
            self.assertIn("assignment", matrix[("mypy", mode, "DC02")]["diagnostic_rules"])
            self.assertEqual(matrix[("mypy", mode, "DC03")]["actual_exit_code"], "0")
            self.assertIn("C2", matrix[("mypy", mode, "DC03")]["reveal_type_output"])
        self.assertEqual(matrix[("Pyright", "standard", "DC01")]["actual_exit_code"], "0")
        self.assertEqual(matrix[("Pyright", "strict", "DC01")]["actual_exit_code"], "1")
        self.assertIn("reportAssignmentType", matrix[("Pyright", "standard", "DC02")]["diagnostic_rules"])
        self.assertEqual(matrix[("Pyright", "standard", "DC03")]["actual_exit_code"], "0")
        self.assertEqual(matrix[("Pyright", "strict", "DC03")]["diagnostic_rules"], "reportUnnecessaryIsInstance")
        for fixture in ("DC04", "DC05", "DC06"):
            for checker, mode in (("mypy", "default"), ("mypy", "strict"), ("Pyright", "standard"), ("Pyright", "strict")):
                self.assertEqual(matrix[(checker, mode, fixture)]["actual_exit_code"], "0")
                self.assertIn("C2", matrix[(checker, mode, fixture)]["reveal_type_output"])

    def test_negative_controls_and_claims(self) -> None:
        controls = load("NEGATIVE-CONTROLS.json")
        self.assertEqual(controls["control_count"], 12)
        self.assertEqual(controls["failed_control_count"], 0)
        self.assertTrue(all(item["passed"] for item in controls["controls"]))
        claims = rows("CLAIM-LEDGER.csv")
        self.assertEqual(len(claims), 11)
        self.assertEqual({row["sofa_post_id"] for row in claims}, {
            "0b3591f6-75de-4661-a7a7-ec28193e1518",
            "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
        })
        self.assertEqual({row["final_classification"] for row in claims}, {"CONTRADICTED", "CHECKER_CONFIRMED"})

    def test_archive_and_sha256_ledger(self) -> None:
        archive = load("ARCHIVE.json")
        expected_payload = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path not in {ROOT / "ARCHIVE.json", ROOT / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in archive["files"]}
        self.assertEqual(set(records), expected_payload)
        for relative, record in records.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, record["bytes"], relative)
            self.assertEqual(sha256(path), record["sha256"], relative)
        ledger: dict[str, str] = {}
        for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            self.assertNotIn(relative, ledger)
            ledger[relative] = digest
        expected_ledger = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path != ROOT / "SHA256SUMS.txt"
        }
        self.assertEqual(set(ledger), expected_ledger)
        for relative, digest in ledger.items():
            self.assertEqual(sha256(ROOT / relative), digest, relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
