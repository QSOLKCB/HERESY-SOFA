#!/usr/bin/env python3
"""Standard-library validation for the LOCAL-VERIFY-003 evidence archive."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
SOURCE_COMMIT = "a8d5b1783d5f5096f00504b99f2276f0a9fbff44"
PRIVATE_WORKSTATION_PREFIX = "/" + "home" + "/" + "trent"


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class LocalVerify003Tests(unittest.TestCase):
    maxDiff = None

    def test_required_artifacts(self) -> None:
        for relative in (
            "ARCHIVE.json",
            "BASELINE.json",
            "CLAIM-LEDGER.csv",
            "ENVIRONMENT.json",
            "FIXTURES/metadata-fixtures.json",
            "NEGATIVE-CONTROLS.json",
            "OPEN-ISSUES.md",
            "ORACLE-MATRIX.csv",
            "README.md",
            "REPORT.json",
            "REVIEW.md",
            "SHA256SUMS.txt",
            "SOURCE-IDENTITY.json",
            "SOURCE/broken_first_key.py",
            "SOURCE/policy_literal.py",
            "SOURCE/reference_oracle.py",
            "SOURCE/run_offline_matrix.py",
            "RAW/ENVIRONMENT-COMMANDS.json",
            "RAW/OFFLINE-EXECUTION.json",
            "RAW/OFFLINE-RESULT.json",
            "RAW/PREFLIGHT-Y005-EXPECTATION.json",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_no_symlinks_caches_or_private_workstation_identity(self) -> None:
        for path in ROOT.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            self.assertNotIn(path.name, {"__pycache__", ".pytest_cache", ".mypy_cache"})
            if path.is_file() and path.suffix in {".json", ".md", ".csv", ".py", ".txt"}:
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(PRIVATE_WORKSTATION_PREFIX, text, path)

    def test_baseline_and_historical_boundary(self) -> None:
        baseline = load("BASELINE.json")
        self.assertTrue(baseline["valid"])
        self.assertEqual(baseline["source_commit"], SOURCE_COMMIT)
        self.assertEqual(baseline["origin_main"], SOURCE_COMMIT)
        self.assertEqual(baseline["branch_start_head"], SOURCE_COMMIT)
        self.assertFalse(baseline["historical_evidence_modified"])
        self.assertEqual(baseline["frozen_collection_diff"], [])
        self.assertTrue(all(
            item["ancestor_of_origin_main"]
            for item in baseline["required_merges"].values()
        ))
        expected = {
            "codex_primary_report": "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229",
            "dual_witness_report": "eb14652b5f4c71f6ddf4949551db536b6cc2cc5b14f61803c228099e915a2db3",
            "local_verify_001_report": "0f8c584a08a37fb3c1fb36d86a8926c5845980f85bd3225962fc2ea957182c93",
            "local_verify_002_report": "70f846f41b6d1da12c1e84b3de403ef631cf30dc8447b7a233cb284d758b5009",
            "local_verify_002b_report": "f76e6fea35a7f423017c3e47f4a1b596c5a1fae02489cdc27e18735668bb0a38",
        }
        self.assertEqual(
            {key: item["sha256"] for key, item in baseline["known_frozen_identities"].items()},
            expected,
        )

    def test_source_identity(self) -> None:
        source = load("SOURCE-IDENTITY.json")
        body = source["source"]["body"].encode("utf-8")
        self.assertEqual(hashlib.sha256(body).hexdigest(), source["source"]["body_sha256"])
        self.assertEqual(source["source"]["id"], "1587d009-5e9c-4cac-81fb-bf3acf5aaf49")
        self.assertEqual(source["source"]["agent_name"], "My_Junie")
        self.assertEqual(source["source"]["reply_count"], 0)
        self.assertEqual(source["source"]["reply_ids"], [])
        self.assertEqual(source["read_receipt"]["sofa_mutation_calls"], [])

    def test_environment_identity_and_safety(self) -> None:
        environment = load("ENVIRONMENT.json")
        self.assertEqual(environment["operating_system"]["os_release"]["PRETTY_NAME"], "Ubuntu 26.04.1 LTS")
        self.assertEqual(environment["operating_system"]["kernel_release"], "7.0.0-42-generic")
        self.assertEqual(environment["operating_system"]["architecture"], "x86_64")
        self.assertEqual(environment["python"]["version_output"], "Python 3.14.4")
        self.assertEqual(environment["uv"]["version_output"], "uv 0.12.1 (x86_64-unknown-linux-gnu)")
        self.assertEqual(environment["yt_dlp"]["version_output"], "2026.03.17")
        self.assertEqual(
            environment["yt_dlp"]["critical_file_identities"][0]["sha256"],
            "efc2960e57e96dc67f5f16d911965cc18ab8a36dd3d9050a8d3fba1cd9e9f93c",
        )
        self.assertEqual(environment["yt_dlp"]["package_tree"]["file_count"], 1132)
        self.assertTrue(all(value is False for value in environment["safety"].values()))

    def test_execution_and_determinism(self) -> None:
        execution = load("RAW/OFFLINE-EXECUTION.json")
        result = load("RAW/OFFLINE-RESULT.json")
        self.assertTrue(execution["successful"])
        self.assertEqual([item["exit_code"] for item in execution["runs"]], [0, 0])
        self.assertTrue(all(execution["determinism"].values()))
        self.assertTrue(execution["source_inventory_unchanged"])
        self.assertEqual(result["assertions"]["count"], 816)
        self.assertEqual(result["assertions"]["negative_control_count"], 709)
        self.assertEqual(result["assertions"]["failed_count"], 0)
        self.assertEqual(result["yt_dlp_integration"]["network_attempt_count"], 0)
        self.assertEqual(result["fixture_results"]["fixture_count"], 40)
        self.assertEqual(result["fixture_results"]["permutation_evaluations"], 73)
        self.assertEqual(result["seeded_stress"]["reorder_checks"], 640)
        self.assertEqual(result["seeded_stress"]["seed"], 26051105)
        self.assertEqual(result["fixture_source"]["sha256"], sha256(ROOT / result["fixture_source"]["path"]))
        for name, digest in result["source_hashes"].items():
            self.assertEqual(digest, sha256(ROOT / "SOURCE" / name), name)

    def test_oracle_matrix_and_decisions(self) -> None:
        matrix = rows("ORACLE-MATRIX.csv")
        self.assertEqual(len(matrix), 40)
        self.assertEqual(sum(item["oracle_decision"] == "SELECT" for item in matrix), 23)
        self.assertEqual(sum(item["oracle_decision"] == "ABSTAIN" for item in matrix), 17)
        self.assertEqual(sum(item["agreement"] == "true" for item in matrix), 26)
        self.assertEqual(sum(item["agreement"] == "false" for item in matrix), 14)
        self.assertTrue(all(item["pass_fail"] == "PASS" for item in matrix))
        self.assertTrue(all(item["evidence_class"] == "EXECUTED_SYNTHETIC" for item in matrix))
        self.assertTrue(all(item["subtitle_downloaded_and_verified"] == "NOT_TESTED" for item in matrix))
        by_id = {item["fixture_id"]: item for item in matrix}
        self.assertEqual(by_id["F002"]["oracle_decision"], "ABSTAIN")
        self.assertEqual(by_id["F004"]["oracle_language"], "en-orig")
        self.assertEqual(by_id["F005"]["oracle_decision"], "ABSTAIN")
        self.assertEqual(by_id["F009"]["oracle_origin"], "automatic")
        self.assertEqual(by_id["F010"]["oracle_origin"], "manual")
        self.assertEqual(by_id["F015"]["oracle_reason"], "conflicting_metadata_hints")
        self.assertEqual(by_id["F023"]["oracle_language"], "en")

    def test_installed_ytdlp_controls(self) -> None:
        result = load("RAW/OFFLINE-RESULT.json")
        observations = {
            item["id"]: item
            for item in result["yt_dlp_integration"]["observations"]
        }
        self.assertEqual(result["yt_dlp_integration"]["version"], "2026.03.17")
        self.assertTrue(all(item["passed"] for item in observations.values()))
        self.assertTrue(observations["Y002"]["selected"]["de-DE"]["url"].endswith("Y002-manual"))
        self.assertEqual(observations["Y005"]["selected"], {})
        self.assertEqual(observations["Y007"]["selected_languages"], ["de", "fr"])
        self.assertEqual(observations["Y008"]["selected_languages"], ["de-DE", "de-DE"])
        self.assertEqual(observations["Y009"]["exception"]["type"], "IndexError")
        self.assertIn("subtitle download", result["yt_dlp_integration"]["not_proved"])

    def test_negative_controls_and_claim_boundaries(self) -> None:
        controls = load("NEGATIVE-CONTROLS.json")
        self.assertEqual(controls["control_count"], 709)
        self.assertEqual(controls["failed_control_count"], 0)
        self.assertEqual(sum(item["count"] for item in controls["groups"]), 709)
        self.assertTrue(all(item["passed"] for item in controls["groups"]))
        claims = rows("CLAIM-LEDGER.csv")
        self.assertEqual(len(claims), 9)
        self.assertEqual(sum(item["evidence_class"] == "NOT_TESTED" for item in claims), 3)
        self.assertEqual(sum(item["evidence_class"] == "EXECUTED_SYNTHETIC" for item in claims), 5)
        self.assertEqual(sum(item["evidence_class"] == "EXECUTED_NATIVE_OFFLINE" for item in claims), 1)
        self.assertTrue(all(item["post_id"] == "1587d009-5e9c-4cac-81fb-bf3acf5aaf49" for item in claims))

    def test_preflight_failure_is_preserved(self) -> None:
        preflight = load("RAW/PREFLIGHT-Y005-EXPECTATION.json")
        self.assertEqual(preflight["exit_code"], 1)
        self.assertEqual(preflight["classification"], "HARNESS_PREFLIGHT_FAILURE")
        self.assertEqual(preflight["network_attempt_count"], 0)
        self.assertEqual(preflight["observed"]["process_subtitles_result"], {})

    def test_archive_and_checksum_ledger(self) -> None:
        archive = load("ARCHIVE.json")
        expected_payload = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path not in {ROOT / "ARCHIVE.json", ROOT / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in archive["files"]}
        self.assertEqual(archive["repository_base_commit"], SOURCE_COMMIT)
        self.assertEqual(set(records), expected_payload)
        self.assertEqual(archive["file_count_excluding_metadata"], len(records))
        for relative, record in records.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, record["bytes"], relative)
            self.assertEqual(sha256(path), record["sha256"], relative)
            self.assertEqual(git_blob(path), record["git_blob_sha"], relative)

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
