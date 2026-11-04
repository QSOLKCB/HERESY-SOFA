#!/usr/bin/env python3
"""Standard-library validation of LOCAL-VERIFY-002 evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
SOURCE_COMMIT = "ddccc1214b7a5d5942c6755ffa4da2c144d0f6ad"


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class LocalVerify002Tests(unittest.TestCase):
    maxDiff = None

    def test_required_artifacts(self) -> None:
        for relative in (
            "ENVIRONMENT.json",
            "CHECKER-MATRIX.csv",
            "CLAIM-LEDGER.csv",
            "REPORT.json",
            "REVIEW.md",
            "NEGATIVE-CONTROLS.json",
            "OPEN-ISSUES.md",
            "RUNTIME-MATRIX.csv",
            "SOURCE-IDENTITY.json",
            "BASELINE.json",
            "ARCHIVE.json",
            "SHA256SUMS.txt",
            "RAW/EXECUTION.json",
            "RAW/PREFLIGHT-FAILURE-20261104T215119Z.json",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_no_symlinks_or_generated_caches(self) -> None:
        for path in ROOT.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            self.assertNotIn(path.name, {"__pycache__", ".mypy_cache", ".pytest_cache"})

    def test_baseline_and_historical_boundary(self) -> None:
        baseline = load("BASELINE.json")
        self.assertEqual(baseline["source_commit"], SOURCE_COMMIT)
        self.assertFalse(baseline["historical_evidence_modified"])
        self.assertEqual(baseline["frozen_collection_diff"], [])
        self.assertTrue(all(
            item["ancestor_of_source_commit"]
            for item in baseline["required_merges"].values()
        ))
        self.assertEqual(
            baseline["known_frozen_identities"]["local_verify_001_report_sha256"],
            "0f8c584a08a37fb3c1fb36d86a8926c5845980f85bd3225962fc2ea957182c93",
        )

    def test_environment_and_tool_scope(self) -> None:
        env = load("ENVIRONMENT.json")
        self.assertEqual(env["operating_system"]["os_release"]["PRETTY_NAME"], "Ubuntu 26.04.1 LTS")
        self.assertEqual(env["operating_system"]["kernel_release"], "7.0.0-42-generic")
        self.assertEqual(env["operating_system"]["architecture"], "x86_64")
        self.assertEqual(set(env["tools"]["python"]), {"3.11.15", "3.12.13", "3.13.14", "3.14.4"})
        self.assertIn("mypy 1.19.1", env["tools"]["mypy"]["version_output"])
        self.assertEqual(env["tools"]["mypy_2.3.1"]["status"], "NOT_TESTED")
        self.assertEqual(env["tools"]["pyright_1.1.414"]["status"], "NOT_TESTED")
        self.assertFalse(env["safety"]["npm_invoked"])
        self.assertFalse(env["safety"]["npx_invoked"])
        inventory = load("RAW/tool-inventory.json")
        self.assertEqual(inventory["executables"]["pyright"], None)
        self.assertEqual(inventory["pyright_bounded_cache_search"]["name_matches"], [])
        self.assertEqual(inventory["pyright_bounded_cache_search"]["npm_index_content_matches"], [])
        for key in ("mypy_1_19_1_offline_probe", "mypy_2_3_1_offline_probe"):
            command = inventory["commands"][key]
            self.assertEqual(command["exit_code"], 1)
            self.assertIn("was not found in the cache", command["stderr"])

    def test_source_identity_and_verbatim_fixtures(self) -> None:
        source = load("SOURCE-IDENTITY.json")
        self.assertEqual(
            source["frozen_snapshot"]["sha256"],
            "fe08d12cd6082f5db22ddd57f9e69f6f15a38f265d7bd483cdd75888cbca640b",
        )
        expected = {
            "GA01": "cd557e23528bb459525391171c07cce3fddcb771d2fb8613e5c121ed1e87efe5",
            "GA03": "71b919736a377dc881ca6f5653c06603ee27da12b35651bea92a8fe7dffeea8c",
            "DC01": "c7d3943c84a06152126ddd20df6115544ffe614a4e56a6e55a031f3d0dd3dc7c",
        }
        for item in source["verbatim_fixture_checks"]:
            self.assertTrue(item["byte_identical"])
            self.assertEqual(item["fixture_sha256"], expected[item["fixture_id"]])

        snapshot = load("../LOCAL-VERIFY-001/CROSS-CHECKS/current-sofa-source-snapshot.json")
        posts = {entry["response"]["data"]["id"]: entry["response"]["data"] for entry in snapshot["posts"]}
        ga_reply = next(
            reply for reply in posts["0b3591f6-75de-4661-a7a7-ec28193e1518"]["replies"]
            if reply["id"] == "a66cf887-724d-41f9-843f-d0d9548b0b84"
        )
        extracts = {
            "GA01": re.findall(r"```py\n(.*?)```", ga_reply["body"], re.S)[0],
            "GA03": re.findall(
                r"```python\n(.*?)```",
                posts["0b3591f6-75de-4661-a7a7-ec28193e1518"]["body"],
                re.S,
            )[1],
            "DC01": re.findall(
                r"```python\n(.*?)```",
                posts["fa8ac823-1616-4df3-9f73-feaa8b5b4bf7"]["body"],
                re.S,
            )[0],
        }
        fixture_files = {
            "GA01": "GA01-original-genericalias-reply.py",
            "GA03": "GA03-custom-class-getitem-source.py",
            "DC01": "DC01-original-posted-dataclass.py",
        }
        for fixture_id, text in extracts.items():
            self.assertEqual((ROOT / "FIXTURES" / fixture_files[fixture_id]).read_bytes(), text.encode("utf-8"))

    def test_execution_receipt_and_determinism(self) -> None:
        execution = load("RAW/EXECUTION.json")
        self.assertEqual(execution["fixture_count"], 14)
        self.assertEqual(execution["mypy_executed_result_rows"], 28)
        self.assertEqual(execution["runtime_result_rows"], 56)
        self.assertEqual(execution["mypy_fresh_process_command_count"], 56)
        self.assertEqual(execution["runtime_fresh_process_command_count"], 112)
        self.assertEqual(execution["check_count"], 195)
        self.assertEqual(execution["failed_check_count"], 0)
        self.assertEqual(execution["negative_control_count"], 11)
        self.assertTrue(execution["source_inventory_unchanged"])
        determinism = load("RAW/determinism.json")
        self.assertTrue(determinism["source_unchanged"])
        self.assertTrue(determinism["all_pairs_identical"])
        self.assertEqual(determinism["mypy_fresh_process_pairs"], 28)
        self.assertEqual(determinism["runtime_fresh_process_pairs"], 56)

    def test_checker_matrix(self) -> None:
        rows = csv_rows("CHECKER-MATRIX.csv")
        self.assertEqual(len(rows), 84)
        executed = [row for row in rows if row["evidence_class"] == "CHECKER_CONFIRMED"]
        untested = [row for row in rows if row["evidence_class"] == "NOT_TESTED"]
        self.assertEqual(len(executed), 28)
        self.assertEqual(len(untested), 56)
        self.assertEqual({row["mode"] for row in executed}, {"default", "strict"})
        self.assertEqual({row["checker"] for row in untested}, {"mypy", "Pyright"})

        by_key = {(row["mode"], row["fixture_id"]): row for row in executed}
        for mode in ("default", "strict"):
            self.assertIn("attr-defined", by_key[(mode, "GA01")]["diagnostic_codes"])
            self.assertIn("operator", by_key[(mode, "GA02")]["diagnostic_codes"])
            self.assertEqual(by_key[(mode, "GA03")]["actual_exit_code"], "0")
            self.assertIn("misc", by_key[(mode, "GA05")]["diagnostic_codes"])
            self.assertIn("type-arg", by_key[(mode, "GA06")]["diagnostic_codes"])
            self.assertIn("var-annotated", by_key[(mode, "DC01")]["diagnostic_codes"])
            self.assertIn("assignment", by_key[(mode, "DC02")]["diagnostic_codes"])
            self.assertIn("C2", by_key[(mode, "DC03")]["reveal_type_output"])
            for fixture_id in ("DC03", "DC04", "DC05", "DC06"):
                self.assertEqual(by_key[(mode, fixture_id)]["actual_exit_code"], "0")

    def test_runtime_matrix(self) -> None:
        rows = csv_rows("RUNTIME-MATRIX.csv")
        self.assertEqual(len(rows), 56)
        self.assertEqual({row["python_version"] for row in rows}, {"3.11.15", "3.12.13", "3.13.14", "3.14.4"})
        by_key = {(row["python_version"], row["fixture_id"]): row for row in rows}
        for version in ("3.11.15", "3.12.13", "3.13.14", "3.14.4"):
            self.assertEqual(by_key[(version, "GA01")]["actual_exit_code"], "1")
            self.assertIn("not subscriptable", by_key[(version, "GA01")]["observed"])
            self.assertIn("unchecked", by_key[(version, "GA02")]["observed"])
            self.assertIn("Ellipsis", by_key[(version, "GA05")]["observed"])
            self.assertIn('"runtime_var_type": "C"', by_key[(version, "DC03")]["observed"])
            for fixture_id in ("DC04", "DC05", "DC06"):
                self.assertIn('"runtime_var_type": "C2"', by_key[(version, fixture_id)]["observed"])

    def test_negative_controls_and_claim_ledger(self) -> None:
        negatives = load("NEGATIVE-CONTROLS.json")
        self.assertEqual(negatives["control_count"], 11)
        self.assertEqual(negatives["failed_control_count"], 0)
        self.assertTrue(all(item["passed"] for item in negatives["controls"]))
        claims = csv_rows("CLAIM-LEDGER.csv")
        self.assertEqual(len(claims), 10)
        self.assertEqual({row["post_id"] for row in claims}, {
            "0b3591f6-75de-4661-a7a7-ec28193e1518",
            "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
        })
        self.assertTrue(all(row["evidence_class"] in {
            "EXECUTED_NATIVE", "CHECKER_CONFIRMED", "DOCUMENTATION_ONLY", "NOT_TESTED", "CONTRADICTED",
        } for row in claims))

    def test_failed_preflight_is_preserved(self) -> None:
        failure = load("RAW/PREFLIGHT-FAILURE-20261104T215119Z.json")
        self.assertEqual(failure["exit_code"], 1)
        self.assertEqual(failure["classification"], "HARNESS_PREFLIGHT_FAILURE")
        self.assertIn("copyright", failure["finding"])
        self.assertFalse(failure["network_access"])

    def test_archive_and_sha256_ledger(self) -> None:
        archive = load("ARCHIVE.json")
        expected_payload = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path not in {ROOT / "ARCHIVE.json", ROOT / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in archive["files"]}
        self.assertEqual(set(records), expected_payload)
        self.assertEqual(archive["file_count_excluding_metadata"], len(records))
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
