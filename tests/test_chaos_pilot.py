"""Offline CHAOS tests: no credentials, network, subprocess or model execution."""
import hashlib
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from chaos_pilot.api import make_request, plan_review, validate_evidence
from chaos_pilot.budget import BudgetExhausted, Ledger, STOP_MICRO_USD
from chaos_pilot.core import SCOPE, cases, compare_snapshot, validate_receipt
from chaos_pilot.__main__ import main


REPO = "QSOLKCB/HERESY-SOFA"
SHA = SCOPE[REPO]
WORKFLOW = ".github/workflows/ci.yml"


class ChaosPilotTests(unittest.TestCase):
    def test_case_manifest_only_has_pinned_targets(self):
        self.assertEqual(len(cases()), 3)
        self.assertTrue(all(set(c["comparison_repositories"]) <= set(SCOPE) for c in cases()))

    def test_dry_run_has_no_cost_or_calls(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["dry-run"]), 0)
        doc = json.loads(stdout.getvalue())
        self.assertEqual(doc["api_calls"], 0)
        self.assertEqual(doc["api_spend_usd"], 0)

    def test_compare_only_accepts_pinned_repo_sha_and_raw_bytes(self):
        good = compare_snapshot(REPO, SHA, WORKFLOW, b"on: pull_request\n")
        self.assertEqual(good["flags"], [])
        self.assertTrue(validate_receipt(good))
        with self.assertRaises(ValueError):
            compare_snapshot("random/evil", SHA, WORKFLOW, b"hello")
        with self.assertRaises(ValueError):
            compare_snapshot(REPO, "0" * 40, WORKFLOW, b"hello")
        with self.assertRaises(ValueError):
            compare_snapshot(REPO, SHA, "../secret", b"hello")
        with self.assertRaises(ValueError):
            compare_snapshot(REPO, SHA, WORKFLOW, "not bytes")

    def test_workflow_flags_are_review_only(self):
        text = b"on:\n  pull_request_target:\nsteps:\n  - run: echo ${{ github.event.pull_request.title }}\n"
        receipt = compare_snapshot(REPO, SHA, WORKFLOW, text)
        self.assertIn("privileged_pr_trigger_review", receipt["flags"])
        self.assertIn("expression_in_run_line_review", receipt["flags"])
        self.assertNotIn("confirmed", receipt["status"])

    def test_private_key_boundary_rejects(self):
        with self.assertRaises(ValueError):
            validate_evidence("-----BEGIN PRIVATE KEY-----")
        with self.assertRaises(ValueError):
            validate_evidence("Authorization: Bearer secret-goes-here")
        with self.assertRaises(ValueError):
            validate_evidence("")

    def test_review_template_is_never_executed(self):
        d = json.loads(make_request("CODECOV-2021", "No sensitive code included."))
        self.assertFalse(d["store"])
        self.assertEqual(d["tools"], [])
        self.assertEqual(d["tool_choice"], "none")
        self.assertEqual(d["reasoning"], {"effort": "high"})
        self.assertEqual(d["model"], "gpt-6.1-sol")

    def test_offline_plan_ignores_key_and_does_not_contact_network(self):
        with tempfile.TemporaryDirectory() as directory:
            note = Path(directory) / "reviewed.txt"
            note.write_bytes(b"Private reviewed notes about build configurations")
            captured = StringIO()
            with patch.dict(os.environ, {"OPENAI_API_KEY": "MUST-NOT-BE-USED"}):
                with patch("urllib.request.urlopen", side_effect=AssertionError("network used")):
                    self.assertEqual(
                        main(["plan-review", "--case", "CODECOV-2021",
                              "--reviewed-evidence", str(note)]), 0
                    )
                    with redirect_stdout(captured):
                        self.assertEqual(
                            main(["plan-review", "--case", "CODECOV-2021",
                                  "--reviewed-evidence", str(note)]), 0
                        )
            result = json.loads(captured.getvalue())
            self.assertEqual(result["status"], "offline_plan_only")
            self.assertEqual(result["api_calls"], 0)
            self.assertEqual(result["api_spend_usd"], 0)
            self.assertEqual(len(result["packet_sha256"]), 64)
            self.assertGreater(result["estimated_reservation_micro_usd"], 0)
            self.assertNotIn("Private reviewed notes", captured.getvalue())
            self.assertNotIn("MUST-NOT-BE-USED", captured.getvalue())
            self.assertFalse((Path(directory) / ".chaos-state").exists())

    def test_live_api_integration_absent_from_repository_module(self):
        import chaos_pilot.api as api
        source = Path(api.__file__).read_text(encoding="utf-8")
        for forbidden in ("urllib.request", "OPENAI_API_KEY", "paid_once(",
                          "request_sender", "Bearer "):
            self.assertNotIn(forbidden, source)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            main(["paid-once"])
        self.assertEqual(caught.exception.code, 2)

    def test_review_plan_fails_closed_for_unknown_case_and_evidence(self):
        with self.assertRaises(ValueError):
            plan_review("NOT-APPROVED", "evidence")
        with self.assertRaises(ValueError):
            plan_review("CODECOV-2021", "Authorization: Bearer private")
        with self.assertRaises(ValueError):
            plan_review("CODECOV-2021", "x" * 6001)

    def test_offline_budget_reservation_and_settlement(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(directory)
            reserve_id = ledger.reserve(b"test", 100)
            self.assertGreater(ledger.total(), 0)
            result = ledger.settle(reserve_id, {"input_tokens": 8, "output_tokens": 12})
            self.assertEqual(result, 144)
            self.assertEqual(ledger.total(), 144)
            with self.assertRaises(ValueError):
                ledger.settle(reserve_id, None)

    def test_budget_rejects_cost_above_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(directory)
            with ledger.locked():
                ledger.write({"schema_version": 1, "requests": [
                    {"id": "past", "status": "usage_recorded",
                     "charged_micro_usd": STOP_MICRO_USD - 5}
                ]})
            with self.assertRaises(BudgetExhausted):
                ledger.reserve(b"test", 100)

    def test_offline_simulation_retains_uncertain_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(directory)
            identity = ledger.reserve(b"test", 100)
            initial = ledger.total()
            self.assertEqual(ledger.settle(identity, None), initial)
            self.assertEqual(ledger.total(), initial)
            self.assertEqual(ledger.read()["requests"][0]["status"],
                             "unknown_usage_reservation_retained")

    def test_snapshot_hash_preserves_crlf_and_bare_cr_exactly(self):
        samples = [
            b"on:\r\n  pull_request_target:\r\nsteps:\r\n",
            b"on:\r  pull_request_target:\rsteps:\r",
            b"on:\n  pull_request_target:\nsteps:\n",
        ]
        digests = set()
        for raw in samples:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "snapshot.yml"
                source.write_bytes(raw)
                stdout = StringIO()
                with redirect_stdout(stdout):
                    status = main(["compare", "--repo", REPO, "--sha", SHA,
                                   "--path", WORKFLOW, "--snapshot", str(source)])
                self.assertEqual(status, 0)
                report = json.loads(stdout.getvalue())
                self.assertEqual(report["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertTrue(validate_receipt(report))
                digests.add(report["sha256"])
        self.assertEqual(len(digests), 3, "distinct source byte streams were conflated")

    def test_invalid_utf8_snapshot_is_rejected_instead_of_rewritten(self):
        with self.assertRaises(UnicodeError):
            compare_snapshot(REPO, SHA, WORKFLOW, b"\xff")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.yml"
            source.write_bytes(b"\xff")
            with redirect_stderr(StringIO()):
                self.assertEqual(
                    main(["compare", "--repo", REPO, "--sha", SHA,
                          "--path", WORKFLOW, "--snapshot", str(source)]), 2
                )

    def test_overlarge_snapshot_fails_closed(self):
        with self.assertRaises(ValueError):
            compare_snapshot(REPO, SHA, WORKFLOW, b"a" * 256001)


if __name__ == "__main__":
    unittest.main(verbosity=2)
