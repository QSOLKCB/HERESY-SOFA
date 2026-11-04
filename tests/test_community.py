"""Community-desk publication state and SOFA outbound-link policy contracts."""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sofa" / "manifest.json"
SITE = ROOT / "site"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.headings = {}
        self.section_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "section" and attributes.get("id") == "community":
            self.section_count += 1
        if tag == "a":
            self.anchors.append(attributes)
        if tag == "script":
            self.headings.setdefault("scripts", []).append(attributes)


class CommunityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")

    def test_publication_evidence_is_not_misclassified(self):
        m = self.manifest
        self.assertFalse(m["publishing_enabled"])
        self.assertEqual(set(m["community"]), {
            "codex-policy-rejection", "retro-gauntlet", "functional-graph"
        })
        codex = m["community"]["codex-policy-rejection"]
        self.assertEqual(codex["status"], "published_reply")
        self.assertEqual(codex["question_id"], "2fa81e8b-1ead-4745-bb29-7f2e9ba819b4")
        self.assertEqual(codex["reply_id"], "881becd6-01d8-4413-899e-922a29d7a800")
        self.assertEqual(codex["source_commit"], "021fccb046508938c4754982efccfb51d6e8356e")
        self.assertTrue((ROOT / codex["audit"]).is_file())

        retro = m["community"]["retro-gauntlet"]
        self.assertEqual(retro["refers_to_challenge"], "RETRO-GAUNTLET-001")
        self.assertEqual(
            sum(c["id"] == retro["id"] for c in m["challenges"]), 1
        )
        self.assertTrue((ROOT / retro["audit"]).is_file())

        graph = m["community"]["functional-graph"]
        self.assertEqual(graph["status"], "local_audit_no_reply_published")
        self.assertTrue((ROOT / graph["audit"]).is_file())
        report = json.loads((ROOT / graph["executed_report"]).read_text(encoding="utf-8"))
        self.assertEqual(graph["source_sha256"], report["source_sha256"])
        self.assertFalse("reply_id" in graph)

    def test_site_statically_links_all_three_without_new_case_status(self):
        page = self.html
        parsed = Links()
        parsed.feed(page)
        self.assertEqual(parsed.section_count, 1)
        for id_ in ("community-codex", "community-retro", "community-graph"):
            self.assertIn('id="' + id_ + '"', page)
        for question_id in (
            "2fa81e8b-1ead-4745-bb29-7f2e9ba819b4",
            "c5fa3bff-959c-4c28-bcaa-68dd8415697e",
            "67036c1f-629f-404e-b2f8-9622e627146a",
        ):
            self.assertIn(question_id, page)
        self.assertIn("LOCAL AUDIT / NO NEW SOFA REPLY", page)
        self.assertIn("SOURCE INSPECTION", page)
        self.assertIn("LOCAL VERIFIED", page)
        self.assertIn(".community-grid", (SITE / "styles.css").read_text())
        self.assertFalse(any(
            attributes.get("src", "").startswith("http")
            for attributes in parsed.headings.get("scripts", [])
        ))
        for a in parsed.anchors:
            if a.get("target") == "_blank":
                self.assertEqual(a.get("rel"), "noopener noreferrer")

        catalogue = json.loads((SITE / "cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(catalogue["cases"]), 12)
        self.assertEqual(sum(c["status"] == "implemented" for c in catalogue["cases"]), 10)
        self.assertEqual(sum(c["status"] == "placeholder" for c in catalogue["cases"]), 2)

    def test_outbound_link_rule_is_documented_without_automated_enforcement(self):
        policy = (ROOT / "docs/SOFA_POLICY.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        template = (ROOT / "sofa/contribution-template.md").read_text(encoding="utf-8")
        self.assertIn("no outbound URLs", policy.lower())
        self.assertIn("plain-text", agents)
        self.assertIn("no outbound clickable links", template)
        self.assertIn("No autonomous posting", policy)
        self.assertFalse(self.manifest["publishing_enabled"])


if __name__ == "__main__":
    unittest.main()
