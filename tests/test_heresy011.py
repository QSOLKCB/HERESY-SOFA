"""Bounded real Linux HERESY-011 controls and fail-closed receipt checks."""
import json
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.runner import run_experiment, verify_experiment


@unittest.skipUnless(
    platform.system() == "Linux" and platform.machine().lower() in
    ("x86_64", "aarch64", "arm64"),
    "HERESY-011's renameat2 and Linux ABI are not portable",
)
class Heresy011Tests(unittest.TestCase):
    def test_atomic_swap_is_reproduced_and_bounded(self):
        with tempfile.TemporaryDirectory() as path:
            result = run_experiment("HERESY-011", path)
            self.assertEqual(result, 0)
            receipt = json.loads((Path(path) / "HERESY-011.json").read_text())
            self.assertEqual(receipt["status"], "executed")
            observed = receipt["observations"]["observations"]
            self.assertTrue(observed["all_checks_passed"])
            self.assertTrue(all(observed["checks"].values()))
            cases = {(c["mode"], c["substitute"]): c
                     for c in observed["exchange_cases"]}
            self.assertEqual(len(cases), 4)
            self.assertTrue(cases["unsafe", "fifo"]["timed_out"])
            self.assertTrue(cases["unsafe", "symlink"]["head_is_wrong"])
            for kind in ("fifo", "symlink"):
                self.assertEqual(cases["safe", kind]["status"], "rejected")
                self.assertFalse(cases["safe", kind]["timed_out"])
            self.assertEqual(verify_experiment("HERESY-011", path, quiet=True), 0)

    def test_target_flag_is_observed_not_assumed(self):
        script = Path(__file__).resolve().parents[1] / "experiments/HERESY-011/run.py"
        result = subprocess.run(
            [sys.executable, str(script)], capture_output=True,
            text=True, timeout=12, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)["observations"]
        expected = 0o400000 if platform.machine().lower() == "x86_64" else 0o100000
        self.assertEqual(int(observed["observed_o_nofollow_octal"], 8), expected)
        self.assertTrue(observed["checks"]["regular_file_positive_control"])
        if platform.machine().lower() in ("aarch64", "arm64"):
            self.assertTrue(observed["arm64_wrong_x86_flag_follows_symlink"])
        else:
            self.assertEqual(observed["arm64_wrong_x86_flag_follows_symlink"],
                             "not_tested_on_this_architecture")


if __name__ == "__main__":
    unittest.main()
