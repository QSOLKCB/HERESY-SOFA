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
        self.assertEqual(len(entries), 11)
        self.assertEqual([e["id"] for e in entries], [
            f"HERESY-{index:03}" for index in range(1, 12)
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
        self.assertEqual(sum(e["status"] == "implemented" for e in CASES["cases"]), 9)
        self.assertEqual(sum(e["status"] == "placeholder" for e in CASES["cases"]), 2)
        self.assertEqual(sum(bool(e.get("published")) for e in CASES["cases"]), 4)

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
