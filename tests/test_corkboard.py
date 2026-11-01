"""Static Pages checks: catalogue provenance, internal links and zero build tooling.

These tests do not pretend to be browser rendering tests. GitHub Pages serves
only reviewed, versioned static files. Incident receipt data is not embedded.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CASES = json.loads((SITE / "cases.json").read_text(encoding="utf-8"))


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.has_main = False
        self.dialogs = []
        self.dialog_labels = {}
        self.canvases = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "main":
            self.has_main = True
        if tag == "dialog":
            self.dialogs.append(attributes.get("id"))
            self.dialog_labels[attributes.get("id")] = attributes.get("aria-labelledby")
        if tag == "canvas":
            self.canvases.append(attributes.get("id"))
        if tag == "script" and "src" in attributes:
            self.paths.append(attributes["src"])
        if tag == "link" and attributes.get("rel") in ("stylesheet", "icon"):
            self.paths.append(attributes["href"])


class CorkboardTests(unittest.TestCase):
    def test_catalogue_exact_case_manifest_identity_and_status(self):
        entries = CASES["cases"]
        self.assertEqual(CASES["schema"], 1)
        self.assertEqual(len(entries), 12)
        self.assertEqual([e["id"] for e in entries], [
            f"HERESY-{index:03}" for index in range(1, 13)
        ])
        for entry in entries:
            with self.subTest(entry=entry["id"]):
                case = entry["id"]
                manifest = json.loads(
                    (ROOT / "experiments" / case / "experiment.json").read_text()
                )
                self.assertEqual(entry["status"], manifest["status"])
                self.assertEqual(entry["formal"], manifest["title"])
                self.assertEqual(entry["doc"], f"experiments/{case}/experiment.md")
                self.assertTrue((ROOT / entry["doc"]).is_file())
                self.assertTrue(entry["name"])
                self.assertTrue(entry["cause"])
                self.assertTrue(entry["finding"])
                self.assertTrue(entry["mitigation"])
                self.assertTrue(entry["scope"])
                self.assertTrue(entry["tags"])
                if entry["status"] == "placeholder":
                    self.assertNotIn("published", entry)
                    self.assertIn("NOT TESTED", entry["scope"])

    def test_contributions_only_claim_verified_manifest_publications(self):
        manifest = json.loads((ROOT / "sofa" / "manifest.json").read_text())
        for entry in CASES["cases"]:
            with self.subTest(entry=entry["id"]):
                published = entry.get("published")
                if not published:
                    continue
                group = "blueprints" if published == "blueprint" else "replies"
                matching = manifest["experiments"][entry["id"]][group]
                self.assertTrue(any(
                    x["id"] == entry["sofaId"] and x["state"] == "published"
                    for x in matching
                ))
        self.assertEqual(sum(e["status"] == "implemented" for e in CASES["cases"]), 10)
        self.assertEqual(sum(e["status"] == "placeholder" for e in CASES["cases"]), 2)
        self.assertEqual(sum(bool(e.get("published")) for e in CASES["cases"]), 4)

    def test_heresy012_is_an_independent_reproduction_not_a_sofa_publication(self):
        entry = next(case for case in CASES["cases"] if case["id"] == "HERESY-012")
        manifest = json.loads(
            (ROOT / "experiments" / "HERESY-012" / "experiment.json").read_text()
        )
        sofa = json.loads((ROOT / "sofa" / "manifest.json").read_text())
        self.assertEqual(entry["formal"], manifest["title"])
        self.assertEqual(entry["status"], "implemented")
        self.assertEqual(entry["category"], "SECURITY")
        self.assertIn("synthetic", entry["finding"].lower())
        self.assertIn("separate upstream evidence", entry["scope"].lower())
        self.assertNotIn("sofaId", entry)
        self.assertNotIn("published", entry)
        self.assertFalse(sofa["publishing_enabled"])
        self.assertEqual(
            sofa["experiments"]["HERESY-012"],
            {"questions": [], "tils": [], "blueprints": [], "playbooks": [], "replies": []},
        )
        self.assertTrue((ROOT / "incidents" / "HERESY-012.md").is_file())
        self.assertTrue((ROOT / "blueprints" / "HERESY-012" / "BLUEPRINT.md").is_file())

    def test_canvas_threads_only_connect_known_cases(self):
        known = {e["id"] for e in CASES["cases"]}
        seen = set()
        for pair in CASES["connections"]:
            self.assertEqual(len(pair), 2)
            self.assertNotEqual(pair[0], pair[1])
            self.assertTrue(set(pair).issubset(known))
            key = tuple(sorted(pair))
            self.assertNotIn(key, seen)
            seen.add(key)

    def test_dialog_name_resolves_to_selected_case_heading(self):
        # Structural check, not a claimed assistive-technology/browser test.
        parser = Assets()
        parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(parser.dialog_labels.get("case-dialog"), "dialog-title")
        js = (SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn('const heading = make("h2", "dossier-title", item.name);', js)
        self.assertIn('heading.id = "dialog-title";', js)
        self.assertIn("body.append(heading);", js)
        self.assertIn("detail.replaceChildren();", js)

    def test_canvas_redraw_lifecycle_covers_transform_and_reversal(self):
        # Regression contract for dynamically positioned pins. CSS transforms
        # do not trigger ResizeObserver; only a real browser can verify pixels.
        js = (SITE / "app.js").read_text(encoding="utf-8")
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn('event.propertyName !== "transform"', js)
        self.assertIn('["transitionrun", "transitionend", "transitioncancel"]', js)
        self.assertIn('root.addEventListener(type, trackCardTransition)', js)
        self.assertIn("activeTransitions.add(event.target)", js)
        self.assertIn("activeTransitions.delete(event.target)", js)
        self.assertIn("if (activeTransitions.size > 0) requestDrawing();", js)
        for event in ("pointerenter", "pointerleave", "focus", "blur"):
            self.assertIn(event, js)
        self.assertIn(".case-card:hover,.case-card:focus-visible", css)
        self.assertIn("transition:transform", css)
        self.assertIn("getBoundingClientRect()", js)
        self.assertIn("@media(prefers-reduced-motion:reduce)", css)

    def test_evidence_and_mitigation_text_are_searchable(self):
        # The browser implements search; this test guards its search corpus and
        # confirms Codex's concrete missing-term examples are in the catalogue.
        js = (SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn("item.cause,item.finding,item.mitigation,item.teaser", js)
        items = {item["id"]: item for item in CASES["cases"]}
        for term, case_id in (
            ("sha-256", "HERESY-010"),
            ("fstat", "HERESY-011"),
            ("idempotent", "HERESY-004"),
        ):
            with self.subTest(term=term, case_id=case_id):
                item = items[case_id]
                displayed = " ".join(
                    str(item[key]) for key in ("cause", "finding", "mitigation")
                ).lower()
                self.assertIn(term, displayed)

    def test_pages_deployment_requires_explicit_main_branch_dispatch(self):
        # Parsing the workflow here is a source contract, not a deployment
        # claim. Pushes and PRs must validate, but must not publish.
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("  push:\n    branches: [main]", workflow)
        self.assertIn("  pull_request:", workflow)
        self.assertIn("  workflow_dispatch:", workflow)
        self.assertIn(
            "if: github.event_name == 'workflow_dispatch' && "
            "github.ref == 'refs/heads/main'",
            workflow,
        )
        self.assertNotIn("if: github.event_name != 'pull_request'", workflow)
        self.assertIn("needs: validate", workflow)

    def test_case_sources_exist_and_no_external_runtime_dependencies(self):
        parser = Assets()
        parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
        self.assertTrue(parser.has_main)
        self.assertIn("case-dialog", parser.dialogs)
        self.assertIn("thread-canvas", parser.canvases)
        self.assertIn("./app.js", parser.paths)
        self.assertIn("./styles.css", parser.paths)
        for path in parser.paths:
            self.assertTrue(path.startswith("./"))
            self.assertTrue((SITE / path.removeprefix("./")).is_file())
        js = (SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn('fetch("./cases.json"', js)
        self.assertIn('getContext("2d")', js)
        self.assertIn("showModal", js)
        self.assertNotIn("localStorage", js)
        self.assertNotIn("sendBeacon", js)
        self.assertFalse(re.search(r"<script[^>]+src=[\"']https?://", (SITE / "index.html").read_text()))


if __name__ == "__main__":
    unittest.main()
