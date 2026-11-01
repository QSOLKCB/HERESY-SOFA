"""Executed-claim and fail-closed receipt checks for HERESY-007/009/010."""
import contextlib
import io
import json
import runpy
import sqlite3
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.runner import ROOT, ExperimentError, run_experiment, verify_experiment


class ThreeEdgeCases(unittest.TestCase):
    def test_three_experiments_generate_valid_executed_receipts(self):
        for identifier in ("HERESY-007", "HERESY-009", "HERESY-010"):
            with self.subTest(identifier=identifier), tempfile.TemporaryDirectory() as directory:
                self.assertEqual(run_experiment(identifier, directory), 0)
                receipt = json.loads((Path(directory) / (identifier + '.json')).read_text())
                self.assertEqual(receipt['status'], 'executed')
                self.assertEqual(receipt['exit_code'], 0)
                observed = receipt['observations']['observations']
                self.assertTrue(observed['all_checks_passed'])
                self.assertTrue(observed['checks'])
                self.assertTrue(all(observed['checks'].values()))
                self.assertEqual(set(receipt['observations']['claims'].values()), {'executed'})
                self.assertEqual(verify_experiment(identifier, directory, quiet=True), 0)

    def test_immediate_claim_observes_competing_busy_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_experiment("HERESY-009", directory), 0)
            receipt = json.loads(
                (Path(directory) / "HERESY-009.json").read_text(encoding="utf-8")
            )
            observations = receipt["observations"]["observations"]
            self.assertEqual(
                observations["details"]["contender_busy_code"], sqlite3.SQLITE_BUSY
            )
            self.assertIsNone(observations["details"]["contender_claimed_rows"])
            self.assertEqual(observations["details"]["immediate_winners"], [1, 0])
            self.assertTrue(
                observations["checks"]["immediate_claim_handles_contention"]
            )

    def test_replacing_immediate_with_deferred_cannot_certify_contention(self):
        # Explicit negative control from the review: disable BEGIN IMMEDIATE
        # without changing the test's data or application-level claim.
        module = runpy.run_path(
            str(ROOT / "experiments" / "HERESY-009" / "run.py"),
            run_name="heresy009_mutation_test",
        )

        class DeferredConnection(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if sql == "BEGIN IMMEDIATE":
                    sql = "BEGIN DEFERRED"
                return super().execute(sql, *args, **kwargs)

        def deferred_connect(path):
            connection = sqlite3.connect(
                path, timeout=0.5, isolation_level=None, factory=DeferredConnection
            )
            connection.execute("PRAGMA busy_timeout=500")
            return connection

        main = module["main"]
        main.__globals__["connect"] = deferred_connect
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                exit_code = main()
        except sqlite3.OperationalError:
            # A stale-snapshot upgrade is an expected failed experiment.
            exit_code = 1
        self.assertNotEqual(exit_code, 0)
        if output.getvalue().strip():
            report = json.loads(output.getvalue())
            self.assertNotEqual(
                report["claims"]["immediate_claim_handles_contention"], "executed"
            )

    def test_missing_git_cannot_create_successful_diff3_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'PATH': directory}):
                self.assertNotEqual(run_experiment('HERESY-007', directory), 0)
            receipt = json.loads((Path(directory) / 'HERESY-007.json').read_text())
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['exit_code'], 1)
            self.assertEqual(set(receipt['observations']['claims'].values()), {'not_tested'})
            with self.assertRaises(ExperimentError):
                verify_experiment('HERESY-007', directory, quiet=True)