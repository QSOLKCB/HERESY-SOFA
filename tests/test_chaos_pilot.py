"""No network. No external commands. No paid calls. Synthetic evidence only."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chaos_pilot.api import (
    ACKNOWLEDGEMENT, PaidRunError, make_request, paid_once, validate_evidence,
)
from chaos_pilot.budget import (
    BudgetExhausted, Ledger, reserve_cost, STOP_MICRO_USD,
)
from chaos_pilot.core import SCOPE, cases, compare_snapshot, validate_receipt
from chaos_pilot.__main__ import main


class ChaosPilotTests(unittest.TestCase):
    def test_case_manifest_only_has_pinned_targets(self):
        self.assertEqual(len(cases()), 3)
        self.assertTrue(all(set(c["comparison_repositories"]) <= set(SCOPE) for c in cases()))

    def test_dry_run_has_no_cost_or_calls(self):
        from contextlib import redirect_stdout
        from io import StringIO
        s = StringIO()
        with redirect_stdout(s):
            self.assertEqual(main(["dry-run"]), 0)
        doc = json.loads(s.getvalue())
        self.assertEqual(doc["api_calls"], 0)
        self.assertEqual(doc["api_spend_usd"], 0)

    def test_compare_only_accepts_pinned_repo_sha(self):
        sha = SCOPE["QSOLKCB/HERESY-SOFA"]
        good = compare_snapshot("QSOLKCB/HERESY-SOFA", sha, ".github/workflows/x.yml", "on: pull_request\n")
        self.assertEqual(good["flags"], [])
        self.assertTrue(validate_receipt(good))
        with self.assertRaises(ValueError):
            compare_snapshot("random/evil", sha, "ci.yml", "hello")
        with self.assertRaises(ValueError):
            compare_snapshot("QSOLKCB/HERESY-SOFA", "0" * 40, "ci.yml", "hello")
        with self.assertRaises(ValueError):
            compare_snapshot("QSOLKCB/HERESY-SOFA", sha, "../secret", "hello")

    def test_workflow_flags_are_review_only(self):
        text = "on:\n  pull_request_target:\nsteps:\n  - run: echo ${{ github.event.pull_request.title }}\n"
        receipt = compare_snapshot("QSOLKCB/HERESY-SOFA", SCOPE["QSOLKCB/HERESY-SOFA"], ".github/workflows/ci.yml", text)
        self.assertIn("privileged_pr_trigger_review", receipt["flags"])
        self.assertIn("expression_in_run_line_review", receipt["flags"])
        self.assertNotIn("confirmed", receipt["status"])

    def test_private_key_boundary_rejects(self):
        with self.assertRaises(ValueError):
            validate_evidence("-----BEGIN PRIVATE KEY-----")
        with self.assertRaises(ValueError):
            validate_evidence("Authorization: Bearer secret-goes-here")

    def test_request_uses_no_tools_and_no_store(self):
        d = json.loads(make_request("CODECOV-2021", "No sensitive code included."))
        self.assertFalse(d["store"])
        self.assertEqual(d["tools"], [])
        self.assertEqual(d["tool_choice"], "none")
        self.assertEqual(d["reasoning"], {"effort": "high"})
        self.assertEqual(d["model"], "gpt-6.1-sol")

    def test_no_ack_no_call(self):
        with tempfile.TemporaryDirectory() as directory:
            called = []
            with self.assertRaises(PaidRunError):
                paid_once("CODECOV-2021", "reviewed", directory,
                          ack="NO", request_sender=lambda _: called.append(True))
            self.assertEqual(called, [])
            self.assertFalse((Path(directory) / "ledger.json").exists())

    def test_missing_key_no_call_or_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(PaidRunError):
                    paid_once("CODECOV-2021", "reviewed", directory,
                              ack=ACKNOWLEDGEMENT)
            self.assertFalse((Path(directory) / "ledger.json").exists())

    def test_reservation_and_settlement(self):
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
                    {"id": "past", "status": "usage_recorded", "charged_micro_usd": STOP_MICRO_USD - 5}
                ]})
            with self.assertRaises(BudgetExhausted):
                ledger.reserve(b"test", 100)

    def test_success_is_private_report_and_ledgers_usage(self):
        fake = {"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "Private analysis only"}]}
        ], "usage": {"input_tokens": 100, "output_tokens": 30}}
        with tempfile.TemporaryDirectory() as directory:
            result = paid_once("CIRCLECI-2023", "Reviewed public note", directory,
                               ack=ACKNOWLEDGEMENT, request_sender=lambda _: fake)
            self.assertEqual(result["status"], "private_review_pending")
            self.assertIn("Private analysis", Path(result["report_path"]).read_text())
            self.assertEqual(Ledger(directory).total(), 600)
            self.assertNotIn("Reviewed public note", (Path(directory) / "ledger.json").read_text())

    def test_failed_api_keeps_reserved_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            def failing(_):
                raise ConnectionError("test network failure")
            with self.assertRaises(PaidRunError):
                paid_once("CODECOV-2021", "Reviewed text", directory,
                          ack=ACKNOWLEDGEMENT, request_sender=failing)
            ledger = Ledger(directory)
            self.assertGreater(ledger.total(), 0)
            self.assertEqual(ledger.read()["requests"][0]["status"],
                             "unknown_usage_reservation_retained")

    def test_incomplete_response_not_reported_as_success(self):
        response = {"status": "incomplete", "output": [],
                    "usage": {"input_tokens": 3, "output_tokens": 2}}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PaidRunError):
                paid_once("CODECOV-2021", "Reviewed text", directory,
                          ack=ACKNOWLEDGEMENT, request_sender=lambda _: response)
            self.assertFalse(list(Path(directory).glob("report-*.md")))


if __name__ == "__main__":
    unittest.main(verbosity=2)