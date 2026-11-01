"""HERESY-012 independent synthetic JUnit reproduction and receipt contracts.

These tests use the stdlib fixture, not QEC's Pytest suite or Ed25519.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.runner import ExperimentError, run_experiment, verify_experiment

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments" / "HERESY-012" / "run.py"


def _source_module():
    spec = importlib.util.spec_from_file_location("heresy_012_fixture", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JUnitIdentityTests(unittest.TestCase):
    def test_known_parameter_laundering_is_accepted_only_by_flawed_verifier(self):
        module = _source_module()
        genuine = module.make_xml()
        substituted = module.make_xml(parameters=tuple(
            "operation-REVOKED_OPERATION-" + str(i) for i in range(4)
        ))
        self.assertEqual(len(module.EXACT_NODES), 11)
        self.assertTrue(module.original_accepts(genuine))
        self.assertTrue(module.corrected_accepts(genuine))
        self.assertTrue(module.original_accepts(substituted))
        self.assertFalse(module.corrected_accepts(substituted))

    def test_wrong_dimension_reason_missing_and_failed_controls(self):
        module = _source_module()
        bad = module.make_xml(parameters=(
            "operation-REVOKED_SIGNER", *module.DIMENSIONS[1:]
        ))
        self.assertTrue(module.original_accepts(bad))
        self.assertFalse(module.corrected_accepts(bad))
        missing = module.make_xml(omit=(module.SINGLES[0],))
        self.assertFalse(module.original_accepts(missing))
        self.assertFalse(module.corrected_accepts(missing))
        for label in ("failure", "error", "skipped"):
            with self.subTest(label=label):
                xml = module.make_xml(status=label)
                self.assertFalse(module.original_accepts(xml))
                self.assertFalse(module.corrected_accepts(xml))

    def test_harness_records_executed_observations_and_verifies_source_hashes(self):
        with tempfile.TemporaryDirectory(prefix="heresy012-test-") as directory:
            self.assertEqual(run_experiment("HERESY-012", directory), 0)
            receipt = json.loads(
                (Path(directory) / "HERESY-012.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["status"], "executed")
            self.assertEqual(receipt["exit_code"], 0)
            claims = receipt["observations"]["claims"]
            self.assertEqual(
                claims["family_counts_can_launder_missing_parameter_dimensions"],
                "executed",
            )
            self.assertEqual(claims["real_qec_security_tests_executed_here"], "not_tested")
            self.assertEqual(claims["original_qec_run_omitted_revocations"], "unsupported")
            self.assertTrue(all(receipt["observations"]["observations"]["checks"].values()))
            self.assertEqual(
                verify_experiment("HERESY-012", directory, quiet=True), 0
            )
            receipt["evidence"][0]["sha256"] = "0" * 64
            (Path(directory) / "HERESY-012.json").write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            with self.assertRaises(ExperimentError):
                verify_experiment("HERESY-012", directory, quiet=True)

    def test_child_exit_fails_when_required_counterexample_is_broken(self):
        # Copy only a disposable experiment, break the critical assertion's
        # input, and prove the child exit + reported claim cannot remain green.
        source = SOURCE.read_text(encoding="utf-8")
        expected = '"operation_only_old_incorrectly_accepts": original_accepts(operation_only)'
        self.assertEqual(source.count(expected), 1)
        with tempfile.TemporaryDirectory(prefix="heresy012-negative-") as directory:
            test_file = Path(directory) / "broken_case.py"
            test_file.write_text(source.replace(expected,
                '"operation_only_old_incorrectly_accepts": False'), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True, text=True, timeout=10, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            response = json.loads(result.stdout)
            self.assertFalse(response["observations"]["all_checks_passed"])
            self.assertEqual(
                response["claims"]["exact_parameter_identity_check_rejects_substitution"],
                "not_tested",
            )


if __name__ == "__main__":
    unittest.main()
