"""Repository regression tests for the LOCAL-VERIFY-002 evidence archive."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
ROOT = REPOSITORY / "evidence" / "LOCAL-VERIFY-002"


def load(relative: str) -> object:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalVerify002ArchiveTests(unittest.TestCase):
    maxDiff = None

    def test_archive_and_ledger_cover_every_file(self) -> None:
        archive = load("ARCHIVE.json")
        records = {item["path"]: item for item in archive["files"]}
        expected_payload = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path not in {ROOT / "ARCHIVE.json", ROOT / "SHA256SUMS.txt"}
        }
        self.assertEqual(set(records), expected_payload)
        for relative, record in records.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, record["bytes"], relative)
            self.assertEqual(sha256(path), record["sha256"], relative)

        ledger = {}
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

    def test_execution_counts_and_determinism(self) -> None:
        receipt = load("RAW/EXECUTION.json")
        self.assertEqual(receipt["mypy_executed_result_rows"], 28)
        self.assertEqual(receipt["runtime_result_rows"], 56)
        self.assertEqual(receipt["check_count"], 195)
        self.assertEqual(receipt["failed_check_count"], 0)
        self.assertEqual(receipt["negative_control_count"], 11)
        determinism = load("RAW/determinism.json")
        self.assertTrue(determinism["all_pairs_identical"])
        self.assertTrue(determinism["source_unchanged"])

    def test_checker_coverage_is_exact(self) -> None:
        matrix = rows("CHECKER-MATRIX.csv")
        self.assertEqual(len(matrix), 84)
        executed = [row for row in matrix if row["evidence_class"] == "CHECKER_CONFIRMED"]
        untested = [row for row in matrix if row["evidence_class"] == "NOT_TESTED"]
        self.assertEqual(len(executed), 28)
        self.assertEqual(len(untested), 56)
        self.assertEqual({row["checker"] for row in untested}, {"mypy", "Pyright"})
        tool_inventory = load("RAW/tool-inventory.json")
        self.assertEqual(tool_inventory["coverage"], {
            "mypy_1.19.1": "EXECUTED_NATIVE",
            "mypy_2.3.1": "NOT_TESTED",
            "pyright_1.1.414": "NOT_TESTED",
        })
        self.assertFalse(tool_inventory["bootstrap_boundary"]["npm_invoked"])

    def test_generic_alias_and_typevartuple_results(self) -> None:
        matrix = rows("CHECKER-MATRIX.csv")
        default = {
            row["fixture_id"]: row
            for row in matrix
            if row["checker"] == "mypy" and row["version"].startswith("1.19.1") and row["mode"] == "default"
        }
        self.assertIn("attr-defined", default["GA01"]["diagnostic_codes"])
        self.assertIn("operator", default["GA02"]["diagnostic_codes"])
        self.assertIn("misc", default["GA05"]["diagnostic_codes"])

        runtime = rows("RUNTIME-MATRIX.csv")
        by_key = {(row["python_version"], row["fixture_id"]): row for row in runtime}
        for version in ("3.11.15", "3.12.13", "3.13.14", "3.14.4"):
            self.assertIn("not subscriptable", by_key[(version, "GA01")]["observed"])
            self.assertIn("unchecked", by_key[(version, "GA02")]["observed"])
            self.assertIn("Ellipsis", by_key[(version, "GA05")]["observed"])

    def test_dataclass_checker_runtime_divergence(self) -> None:
        matrix = rows("CHECKER-MATRIX.csv")
        default = {
            row["fixture_id"]: row
            for row in matrix
            if row["checker"] == "mypy" and row["version"].startswith("1.19.1") and row["mode"] == "default"
        }
        self.assertIn("assignment", default["DC02"]["diagnostic_codes"])
        self.assertEqual(default["DC03"]["actual_exit_code"], "0")
        self.assertIn("C2", default["DC03"]["reveal_type_output"])
        self.assertIn("var-annotated", default["DC01"]["diagnostic_codes"])

        runtime = rows("RUNTIME-MATRIX.csv")
        by_key = {(row["python_version"], row["fixture_id"]): row for row in runtime}
        for version in ("3.11.15", "3.12.13", "3.13.14", "3.14.4"):
            self.assertIn('"runtime_var_type": "C"', by_key[(version, "DC03")]["observed"])
            for fixture_id in ("DC04", "DC05", "DC06"):
                self.assertIn('"runtime_var_type": "C2"', by_key[(version, fixture_id)]["observed"])

    def test_historical_boundary_and_source_identity(self) -> None:
        baseline = load("BASELINE.json")
        self.assertEqual(baseline["source_commit"], "ddccc1214b7a5d5942c6755ffa4da2c144d0f6ad")
        self.assertFalse(baseline["historical_evidence_modified"])
        self.assertEqual(baseline["frozen_collection_diff"], [])
        source = load("SOURCE-IDENTITY.json")
        self.assertTrue(all(item["byte_identical"] for item in source["verbatim_fixture_checks"]))
        self.assertFalse(source["current_sofa_read"]["mutations"])

    def test_failed_preflight_and_negative_controls_are_preserved(self) -> None:
        failure = load("RAW/PREFLIGHT-FAILURE-20261104T215119Z.json")
        self.assertEqual(failure["exit_code"], 1)
        self.assertIn("copyright", failure["finding"])
        controls = load("NEGATIVE-CONTROLS.json")
        self.assertEqual(controls["control_count"], 11)
        self.assertEqual(controls["failed_control_count"], 0)

    def test_no_generated_caches_or_symlinks(self) -> None:
        self.assertFalse(any(path.is_symlink() for path in ROOT.rglob("*")))
        self.assertFalse(any(path.name in {"__pycache__", ".mypy_cache", ".pytest_cache"} for path in ROOT.rglob("*")))


if __name__ == "__main__":
    unittest.main()
