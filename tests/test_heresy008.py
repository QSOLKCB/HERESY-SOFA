"""Negative controls for HERESY-008's executed-claim contract."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from harness.runner import ExperimentError, run_experiment, verify_experiment

@unittest.skipUnless(os.name == "posix", "Linux/POSIX-first fixture")
class GitDirIncidentTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "Git CLI unavailable")
    def test_disposable_repositories_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_experiment("HERESY-008", directory), 0)
            receipt = json.loads((Path(directory) / "HERESY-008.json").read_text())
            self.assertEqual(receipt["status"], "executed")
            obs = receipt["observations"]["observations"]
            self.assertTrue(obs["all_checks_passed"])
            self.assertTrue(all(obs["checks"].values()))
            self.assertFalse(obs["windows_cmd_executed"])
            self.assertEqual(set(receipt["observations"]["claims"].values()), {"executed"})
            self.assertEqual(verify_experiment("HERESY-008", directory, quiet=True), 0)

    def test_missing_git_cannot_create_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"PATH": directory}):
                self.assertNotEqual(run_experiment("HERESY-008", directory), 0)
            receipt = json.loads((Path(directory) / "HERESY-008.json").read_text())
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(set(receipt["observations"]["claims"].values()),
                             {"unsupported"})
            with self.assertRaises(ExperimentError):
                verify_experiment("HERESY-008", directory, quiet=True)

    def test_noop_git_cannot_invent_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            shim = Path(directory) / "git"
            shim.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then\n'
                            ' echo "git version pretend"\nfi\nexit 0\n',
                            encoding="utf-8")
            shim.chmod(0o755)
            with mock.patch.dict(
                os.environ, {"PATH": directory + os.pathsep + os.environ.get("PATH", "")}
            ):
                self.assertNotEqual(run_experiment("HERESY-008", directory), 0)
            receipt = json.loads((Path(directory) / "HERESY-008.json").read_text())
            self.assertEqual(receipt["status"], "failed")
            self.assertFalse(receipt["observations"]["observations"]["all_checks_passed"])
            self.assertEqual(set(receipt["observations"]["claims"].values()),
                             {"not_tested"})
            with self.assertRaises(ExperimentError):
                verify_experiment("HERESY-008", directory, quiet=True)
