"""Executed-claim and fail-closed receipt checks for HERESY-007/009/010."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.runner import ExperimentError, run_experiment, verify_experiment


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