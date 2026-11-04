"""Byte-identity and scope contracts for FUNCTIONAL-GRAPH-001 evidence archive.

Never rerun third-party verifier scripts or historical tests in these checks.
The uploaded originals must remain immutable: a changed byte is a failure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence" / "FUNCTIONAL-GRAPH-001"
MANIFEST = json.loads((FOLDER / "ARCHIVE.json").read_text(encoding="utf-8"))


class DualWitnessArchiveTests(unittest.TestCase):
    def test_archive_contents_match_sha256_and_lengths(self):
        self.assertEqual(MANIFEST["schema_version"], 1)
        self.assertEqual(MANIFEST["case_id"], "FUNCTIONAL-GRAPH-001")
        self.assertEqual(len(MANIFEST["files"]), 9)
        entries = MANIFEST["files"]
        self.assertEqual(len({x["path"] for x in entries}), 9)
        for item in entries:
            with self.subTest(path=item["path"]):
                path = FOLDER / item["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, item["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
        self.assertEqual(sum(x["path"].startswith("MONICA-001/") for x in entries), 3)
        self.assertEqual(sum(x["path"].startswith("CODEX-001/") for x in entries), 4)
        self.assertEqual(sum(x["path"].startswith("RECONCILIATION/") for x in entries), 2)

    def test_sha256sums_lists_exactly_those_files(self):
        records = {}
        for line in (FOLDER / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            digest, path = line.split("  ", 1)
            self.assertNotIn(path, records)
            records[path] = digest
        self.assertEqual(records, {x["path"]:x["sha256"] for x in MANIFEST["files"]})

    def test_source_and_published_sofa_identity(self):
        source = MANIFEST["source"]
        self.assertEqual(source["commit"], "42af1d99d736802214ed61ffe950e6ad809b1aee")
        self.assertEqual(hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(), source["sha256"])
        pub = MANIFEST["publication"]
        self.assertEqual(pub["reply_id"], "871ae4a2-b826-47f6-945c-e883145e9caf")
        self.assertEqual(pub["question_id"], "67036c1f-629f-404e-b2f8-9622e627146a")
        sofa = json.loads((ROOT / "sofa" / "manifest.json").read_text())
        record = sofa["community"]["functional-graph"]
        self.assertEqual(record["status"], "published_reply")
        self.assertEqual(record["reply_id"], pub["reply_id"])
        self.assertEqual(record["question_id"], pub["question_id"])
        self.assertEqual(record["evidence_archive"], "evidence/FUNCTIONAL-GRAPH-001/ARCHIVE.json")
        self.assertFalse(sofa["publishing_enabled"])

    def test_reported_verdicts_and_canonical_raw_agree(self):
        mraw = json.loads((FOLDER / "MONICA-001/FUNCTIONAL-GRAPH-001-MONICA-RAW.json").read_text())
        m = json.loads((FOLDER / "MONICA-001/FUNCTIONAL-GRAPH-001-MONICA-REPORT.json").read_text())
        craw = json.loads((FOLDER / "CODEX-001/FUNCTIONAL-GRAPH-001-CODEX-RAW.json").read_text())
        c = json.loads((FOLDER / "CODEX-001/FUNCTIONAL-GRAPH-001-CODEX-REPORT.json").read_text())
        for raw in (mraw,craw):
            self.assertEqual(raw["status"], "PASS")
            self.assertEqual(raw["source_sha256"], MANIFEST["source"]["sha256"])
            self.assertEqual(raw["exhaustive_graphs_n2_to_n6"],16739)
        self.assertEqual(m["verification_status"],"PASS")
        self.assertEqual(c["evidence_status"],"PASS")
        self.assertEqual(mraw["benchmarks"], m["canonical_test_results"]["runner_benchmarks"])
        self.assertEqual(craw["benchmarks"], c["canonical_tests"]["runner_result"]["benchmarks"])
        self.assertEqual(m["independent_oracle_results"]["small_graphs_total"], 36749)
        self.assertEqual(m["independent_oracle_results"]["small_graph_algorithm_comparisons"], 183745)
        self.assertEqual(c["independent_execution"]["oracle_results"]["total_graphs"], 46897)
        self.assertEqual(c["independent_execution"]["oracle_results"]["total_candidate_comparisons"], 234485)
        self.assertEqual(len(m["negative_control_outcomes"]), 3)
        self.assertEqual(len(c["independent_execution"]["negative_controls"]), 4)

    def test_preserve_reported_limits(self):
        self.assertIn("microVM", (FOLDER / "README.md").read_text())
        limitations = "\n".join(MANIFEST["limitations"]).lower()
        self.assertIn("supplemental", limitations)
        self.assertIn("unverified", limitations)
        self.assertIn("rss", limitations)
        self.assertIn("etq-303", limitations)


if __name__ == "__main__":
    unittest.main()
