"""Negative controls for HERESY-008's executed-claim contract."""
import json
import os
import shutil
import subprocess
import sys
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


    @unittest.skipUnless(shutil.which("git"), "Git CLI unavailable")
    def test_inherited_global_hook_does_not_escape_fixture(self):
        # This tests the entrypoint directly: the harness intentionally supplies
        # a minimal environment, which otherwise masks this exact failure.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            config = home / ".gitconfig"
            hooks = root / "external hooks"
            hooks.mkdir()
            marker = root / "hook-executed"
            hook = hooks / "pre-commit"
            hook.write_text(
                '#!/bin/sh\nprintf invoked > "' + str(marker) + '"\nexit 42\n',
                encoding="utf-8",
            )
            hook.chmod(0o755)
            config.write_text(
                "[core]\n    hooksPath = " + str(hooks) + "\n",
                encoding="utf-8",
            )
            from harness.runner import ROOT
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["XDG_CONFIG_HOME"] = str(home / ".config")
            env.pop("GIT_CONFIG_GLOBAL", None)
            entrypoint = ROOT / "experiments" / "HERESY-008" / "run.py"
            process = subprocess.run(
                [sys.executable, str(entrypoint)],
                env=env, cwd=root, capture_output=True, text=True,
                timeout=30, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads(process.stdout)
            self.assertTrue(report["observations"]["all_checks_passed"])
            self.assertEqual(set(report["claims"].values()), {"executed"})
            self.assertFalse(marker.exists(), "fixture invoked an inherited pre-commit hook")

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
