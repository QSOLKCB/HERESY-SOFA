"""Registry and published-body integrity tests for SOFA-BAKERS-DOZEN-013."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence" / "SOFA-BAKERS-DOZEN-013"
ARCHIVE = json.loads((FOLDER / "ARCHIVE.json").read_text(encoding="utf-8"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class SofaBakersDozen013Tests(unittest.TestCase):
    def test_archive_manifest_and_sha_ledger(self):
        expected = {
            path.relative_to(FOLDER).as_posix()
            for path in FOLDER.rglob("*")
            if path.is_file() and path not in {FOLDER / "ARCHIVE.json", FOLDER / "SHA256SUMS.txt"}
        }
        records = {item["path"]: item for item in ARCHIVE["files"]}
        self.assertEqual(ARCHIVE["case_id"], "SOFA-BAKERS-DOZEN-013")
        self.assertEqual(set(records), expected)
        for relative, item in records.items():
            data = (FOLDER / relative).read_bytes()
            self.assertEqual(len(data), item["bytes"])
            self.assertEqual(digest(data), item["sha256"])
            self.assertEqual(git_blob(data), item["git_blob_sha"])

        ledger = {}
        for line in (FOLDER / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            value, relative = line.split("  ", 1)
            self.assertNotIn(relative, ledger)
            ledger[relative] = value
        self.assertEqual(ledger, {item["path"]: item["sha256"] for item in ARCHIVE["files"]})

    def test_thirteen_case_registry(self):
        registry = json.loads((FOLDER / "REGISTRY.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["case_count"], 13)
        self.assertEqual(registry["published_count"], 9)
        self.assertEqual(registry["held_count"], 4)
        self.assertEqual([item["case"] for item in registry["entries"]], [f"{i:02d}" for i in range(1, 14)])
        published = [item for item in registry["entries"] if item["published_reply_id"]]
        held = [item for item in registry["entries"] if not item["published_reply_id"]]
        self.assertEqual(len(published), 9)
        self.assertEqual([item["case"] for item in held], ["03", "06", "08", "11"])
        self.assertTrue(all(item["published_reply_verified"] for item in published))
        self.assertTrue(all(not item["published_reply_verified"] for item in held))

    def test_published_replies_match_canonical_snapshots(self):
        snapshots = {}
        for path in sorted(FOLDER.glob("SOFA-SNAPSHOT-PART-*.json")):
            for entry in json.loads(path.read_text(encoding="utf-8"))["entries"]:
                snapshots[entry["n"]] = entry["response"]["data"]

        ledger = json.loads((FOLDER / "PUBLISHED-REPLIES.json").read_text(encoding="utf-8"))
        self.assertEqual(ledger["reply_count"], 9)
        expected_ids = set(ARCHIVE["published_reply_ids"])
        self.assertEqual({item["reply_id"] for item in ledger["replies"]}, expected_ids)
        for item in ledger["replies"]:
            post = snapshots[item["case"]]
            self.assertEqual(post["id"], item["parent_post_id"])
            reply = next(entry for entry in post["replies"] if entry["id"] == item["reply_id"])
            body = reply["body"].encode("utf-8")
            self.assertEqual(reply["agent_name"], "QSOL HERESY — The Compiler Inquisitor")
            self.assertIsNone(reply.get("deleted_at"))
            self.assertEqual(len(body), item["body_bytes"])
            self.assertEqual(digest(body), item["body_sha256"])
            self.assertIn("this archival run did not independently perform or publish", item["authorship_note"])

    def test_evidence_classes_preserve_execution_boundaries(self):
        registry = json.loads((FOLDER / "REGISTRY.json").read_text(encoding="utf-8"))
        classes = {item["case"]: item["evidence_class"] for item in registry["entries"]}
        self.assertEqual(classes["01"], "executed_runtime")
        self.assertEqual(classes["07"], "source_backed_documentation")
        self.assertEqual(classes["09"], "synthetic_experiment_and_proposed_methodology")
        self.assertEqual(classes["10"], "source_backed_documentation_and_synthetic_model")
        self.assertEqual(classes["11"], "not_tested")
        self.assertEqual(classes["13"], "proposed_design_and_methodology")
        self.assertNotIn("trust_score", json.dumps(registry).lower())

    def test_central_manifest_and_backlog(self):
        sofa = json.loads((ROOT / "sofa/manifest.json").read_text(encoding="utf-8"))
        record = sofa["community"]["sofa-bakers-dozen-013"]
        self.assertEqual(record["status"], "nine_published_replies_four_held")
        self.assertEqual(len(record["reply_ids"]), 9)
        self.assertEqual(record["evidence_archive"], "evidence/SOFA-BAKERS-DOZEN-013/ARCHIVE.json")
        self.assertFalse(sofa["publishing_enabled"])
        backlog = (ROOT / "LOCAL-TESTING-BACKLOG.md").read_text(encoding="utf-8")
        for term in ("SwiftData", "Windows 11", "Himalaya/Ortie", "NOT_EXECUTED"):
            self.assertIn(term, backlog)


if __name__ == "__main__":
    unittest.main()
