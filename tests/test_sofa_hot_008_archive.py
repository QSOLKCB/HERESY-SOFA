"""Byte identity and publication-boundary tests for SOFA-HOT-008."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence" / "SOFA-HOT-008"
ARCHIVE = json.loads((FOLDER / "ARCHIVE.json").read_text(encoding="utf-8"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class SofaHot008ArchiveTests(unittest.TestCase):
    def test_outer_manifest_covers_every_collection_file(self):
        expected = {
            path.relative_to(FOLDER).as_posix()
            for path in FOLDER.rglob("*")
            if path.is_file() and path not in {FOLDER / "ARCHIVE.json", FOLDER / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in ARCHIVE["files"]}
        self.assertEqual(ARCHIVE["case_id"], "SOFA-HOT-008")
        self.assertEqual(ARCHIVE["evidence"]["file_count"], len(records))
        self.assertEqual(set(records), expected)
        for relative, item in records.items():
            with self.subTest(path=relative):
                data = (FOLDER / relative).read_bytes()
                self.assertEqual(len(data), item["bytes"])
                self.assertEqual(digest(data), item["sha256"])
                self.assertEqual(git_blob(data), item["git_blob_sha"])

    def test_outer_sha256_ledger_matches_manifest(self):
        records = {}
        for line in (FOLDER / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            value, relative = line.split("  ", 1)
            self.assertNotIn(relative, records)
            records[relative] = value
        self.assertEqual(records, {item["path"]: item["sha256"] for item in ARCHIVE["files"]})

    def test_frozen_witness_identities(self):
        monica = FOLDER / "WITNESSES/MONICA-001/SOFA-HOT-008-MONICA-001-evidence.gz"
        primary = FOLDER / "WITNESSES/CODEX-001-primary/CODEX-001-REPORT.json"
        auxiliary = FOLDER / "WITNESSES/CODEX-001-auxiliary/CODEX-001-REPORT.json"
        self.assertEqual(digest(monica.read_bytes()), "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202")
        self.assertEqual(digest(primary.read_bytes()), "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229")
        self.assertEqual(digest(auxiliary.read_bytes()), "f9c61410ac238a0c54f8b8803bf2954df83b585c137d454574b39a15f6bbfcb2")

        with gzip.open(monica, "rb") as stream:
            tar_bytes = stream.read()
        self.assertEqual(digest(tar_bytes), "83992c3b400a3f35949be73c67d8408ef64762010f56b6218297a1c805740344")
        with tarfile.open(fileobj=__import__("io").BytesIO(tar_bytes), mode="r:") as archive:
            members = archive.getmembers()
        self.assertEqual(len(members), 43)
        self.assertEqual(sum(member.isfile() for member in members), 39)
        self.assertFalse(any(member.issym() or member.islnk() or member.isdev() for member in members))

    def test_primary_custom_ledger_without_executing_witness_code(self):
        root = FOLDER / "WITNESSES/CODEX-001-primary"
        checked = 0
        for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            expected_hash, expected_size, relative = line.split("  ", 2)
            data = (root / relative).read_bytes()
            self.assertEqual(len(data), int(expected_size))
            self.assertEqual(digest(data), expected_hash)
            checked += 1
        self.assertEqual(checked, 53)

    def test_publication_event_is_append_only_and_target_scoped(self):
        root = FOLDER / "RECONCILIATION/PUBLICATION-EVENTS/20261104T180540Z-owner-approved"
        event = json.loads((root / "PUBLICATION-EVENT.json").read_text(encoding="utf-8"))
        receipt = json.loads((root / "CASE-03-PUBLICATION-RECEIPT.json").read_text(encoding="utf-8"))
        self.assertTrue(event["append_only"])
        self.assertEqual(event["mutations"], {"reply_calls": 1, "verification_calls": 0, "vote_calls": 0})
        self.assertEqual(event["cases"][0]["reply_id"], "902f2605-383f-4fc9-b8eb-63e21da55dca")
        self.assertEqual(event["cases"][0]["lifecycle_state"], "published")
        self.assertEqual([item["case"] for item in event["cases"] if item["outcome"] == "HELD_BEFORE_WRITE"], ["04", "05", "06", "08"])
        self.assertTrue(all(item["write_attempts"] == 0 for item in event["cases"][1:]))

        approved = (FOLDER / "RECONCILIATION/SOFA-DRAFTS/CASE-03-dataclass.md").read_bytes()
        published = receipt["readback"]["body"].encode("utf-8")
        self.assertEqual(published, approved[:-1])
        self.assertNotEqual(digest(published), digest(approved))
        self.assertEqual(digest(published), receipt["readback"]["body_sha256"])
        self.assertEqual(receipt["readback"]["final_line"], "More edge case Gremlins for the Goblin God!")

        ledger = {}
        for line in (root / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            value, relative = line.split("  ", 1)
            ledger[relative] = value
        self.assertEqual(set(ledger), {"CASE-03-PUBLICATION-RECEIPT.json", "OWNER-APPROVAL.json", "PREPUBLICATION-SOFA-SNAPSHOT.json", "PUBLICATION-EVENT.json"})
        for relative, value in ledger.items():
            self.assertEqual(digest((root / relative).read_bytes()), value)

    def test_drafts_preserve_publication_policy(self):
        drafts = FOLDER / "RECONCILIATION/SOFA-DRAFTS"
        paths = sorted(drafts.glob("CASE-*.md"))
        self.assertEqual(len(paths), 5)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("More edge case Gremlins for the Goblin God!\n"))
            self.assertNotIn("http://", text.lower())
            self.assertNotIn("https://", text.lower())
            self.assertNotIn("www.", text.lower())

    def test_registry_and_backlog_links(self):
        sofa = json.loads((ROOT / "sofa/manifest.json").read_text(encoding="utf-8"))
        record = sofa["community"]["sofa-hot-008"]
        self.assertEqual(record["status"], "partial_one_published_four_held")
        self.assertEqual(record["reply_id"], "902f2605-383f-4fc9-b8eb-63e21da55dca")
        self.assertEqual(record["evidence_archive"], "evidence/SOFA-HOT-008/ARCHIVE.json")
        backlog = (ROOT / "LOCAL-TESTING-BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("yt-dlp", backlog)
        self.assertIn("SPN2", backlog)
        self.assertIn("mypy 2.3.1", backlog)
        self.assertIn("NOT_EXECUTED", backlog)
        self.assertFalse(sofa["publishing_enabled"])


if __name__ == "__main__":
    unittest.main()
