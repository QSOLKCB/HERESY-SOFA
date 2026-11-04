"""Dependency-free controls for RETRO-001. No external network or production paths."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / "challenges" / "RETRO-GAUNTLET-001" / "run.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("retro_gauntlet", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(os.name == "posix", "POSIX flock, socketpair and directory fsync required")
class RetroGauntletTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()
        cls.report = cls.runner.run_demo()

    def test_inplace_write_failure_and_atomic_replacement(self):
        self.assertEqual(self.report["unsafe_in_place_bytes_after_injected_failure"], 0)
        self.assertTrue(self.report["atomic_precommit_original_preserved"])
        self.assertTrue(self.report["atomic_full_replacement_committed"])

    def test_two_contenders_bypass_exists_lock_but_sidecar_flock_excludes(self):
        self.assertEqual(self.report["naive_lock_owners"], 2)
        self.assertTrue(self.report["stable_lock_second_contender_denied"])
        self.assertTrue(self.report["stable_lock_reacquired_after_release"])

    def test_stream_recv_is_short_and_framing_handles_multiple_messages(self):
        self.assertEqual(self.report["recv_header_bytes_after_two_bytes_sent"], 2)
        self.assertEqual(self.report["two_frames_decoded"], 2)
        self.assertTrue(self.report["oversized_frame_rejected"])
        self.assertTrue(self.report["truncated_frame_eof_rejected"])

    def test_cli_emits_same_machine_readable_observations(self):
        finished = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=HERE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
            check=False,
        )
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertEqual(json.loads(finished.stdout), self.report)


if __name__ == "__main__":
    unittest.main()
