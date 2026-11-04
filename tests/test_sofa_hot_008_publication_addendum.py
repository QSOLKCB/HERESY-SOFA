"""Integrity tests for the SOFA-HOT-008 publication addendum."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
ROOT = REPOSITORY / "evidence/SOFA-HOT-008-PUBLICATION-ADDENDUM-01"
EVENT = ROOT / "SOURCE-EVENT"
ARCHIVE = json.loads((ROOT / "ARCHIVE.json").read_text())


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class SofaHot008PublicationAddendumTests(unittest.TestCase):
    def test_outer_manifest_covers_every_addendum_file(self):
        expected = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and path not in {ROOT / "ARCHIVE.json", ROOT / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in ARCHIVE["files"]}
        self.assertEqual(ARCHIVE["case_id"], "SOFA-HOT-008-PUBLICATION-ADDENDUM-01")
        self.assertEqual(set(records), expected)
        self.assertEqual(ARCHIVE["evidence"]["file_count"], len(records))
        for relative, item in records.items():
            data = (ROOT / relative).read_bytes()
            self.assertEqual(len(data), item["bytes"])
            self.assertEqual(sha256(data), item["sha256"])
            self.assertEqual(git_blob(data), item["git_blob_sha"])

    def test_outer_sha256_ledger_matches_manifest(self):
        ledger = {}
        for line in (ROOT / "SHA256SUMS.txt").read_text().splitlines():
            value, relative = line.split("  ", 1)
            self.assertNotIn(relative, ledger)
            ledger[relative] = value
        self.assertEqual(ledger, {item["path"]: item["sha256"] for item in ARCHIVE["files"]})

    def test_frozen_predecessor_is_unchanged(self):
        predecessor = REPOSITORY / "evidence/SOFA-HOT-008/ARCHIVE.json"
        self.assertEqual(
            sha256(predecessor.read_bytes()),
            "7386b1dd858330637b92c6bbdcef3bc3330dd4c100d2956ec942ba222f4174c7",
        )
        self.assertEqual(
            ARCHIVE["predecessor_head"],
            "bb1eabd27a6606b6c229c32190942bcd9672a261",
        )

    def test_source_event_ledger_and_mutation_boundary(self):
        event = json.loads((EVENT / "PUBLICATION-EVENT.json").read_text())
        self.assertEqual(event["result"], "FOUR_PUBLISHED_ALL_ACCEPTED_UNDER_ONE_FINAL_LF_RULE")
        self.assertEqual([item["case"] for item in event["cases"]], ["04", "05", "06", "08"])
        self.assertEqual(event["mutation_counts"]["reply_calls"], 4)
        for key in ("automatic_retries", "edit_calls", "vote_calls", "verification_calls", "delete_calls"):
            self.assertEqual(event["mutation_counts"][key], 0)

        ledger = {}
        for line in (EVENT / "SHA256SUMS.txt").read_text().splitlines():
            value, relative = line.split("  ", 1)
            ledger[relative] = value
        expected = {path.name for path in EVENT.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt"}
        self.assertEqual(set(ledger), expected)
        for relative, value in ledger.items():
            self.assertEqual(sha256((EVENT / relative).read_bytes()), value)

    def test_offline_validator_accepts_only_the_authorized_transform(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "validate_addendum.py")],
            cwd=REPOSITORY,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["case_count"], 4)
        self.assertEqual(receipt["network_calls"], 0)

    def test_navigation_and_file_types(self):
        self.assertIn(
            "evidence/SOFA-HOT-008-PUBLICATION-ADDENDUM-01/README.md",
            (REPOSITORY / "README.md").read_text(),
        )
        self.assertFalse(any(path.is_symlink() for path in ROOT.rglob("*")))


if __name__ == "__main__":
    unittest.main()
