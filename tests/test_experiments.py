import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness.runner import (
    ExperimentError,
    discover_experiments,
    run_experiment,
    verify_experiment,
)


class ExperimentTests(unittest.TestCase):
    def run_and_read(self, experiment_id):
        receipt_directory = tempfile.TemporaryDirectory()
        self.addCleanup(receipt_directory.cleanup)
        result = run_experiment(experiment_id, receipt_directory.name)
        self.assertEqual(result, 0)
        receipt_path = Path(receipt_directory.name) / (experiment_id + ".json")
        return json.loads(receipt_path.read_text(encoding="utf-8")), receipt_directory.name

    def test_json_overflow_and_mitigations_are_observed(self):
        receipt, _ = self.run_and_read("HERESY-001")
        observations = receipt["observations"]["observations"]
        self.assertTrue(observations["parsed_is_infinite"])
        self.assertEqual(observations["parse_constant_calls"], [])
        self.assertTrue(observations["finite_parse_rejected"])
        self.assertTrue(observations["decimal_is_finite"])
        self.assertTrue(observations["strict_serialization_rejected"])

    def test_heredoc_stdin_collision_and_alternative(self):
        receipt, _ = self.run_and_read("HERESY-002")
        observations = receipt["observations"]["observations"]
        self.assertIn("heredoc supplied Python source", observations["collision_stdout"])
        self.assertEqual(observations["working_stdout"], "pipe payload\n")
        self.assertEqual(observations["working_exit_code"], 0)
        self.assertEqual(observations["consumer_exit_code"], 0)
        self.assertEqual(receipt["observations"]["claims"]["heredoc_occupies_python_stdin"], "executed")
        self.assertEqual(receipt["observations"]["claims"]["command_string_preserves_pipe_stdin"], "executed")

    def test_heredoc_child_interpreter_failure_cannot_pass_receipt(self):
        # Both a missing/interrupted interpreter and a silent no-op shim must fail.
        for child_exit in (127, 0):
            with self.subTest(child_exit=child_exit), tempfile.TemporaryDirectory() as directory:
                shim = Path(directory) / "python3"
                shim.write_text("#!/bin/sh\nexit {}\n".format(child_exit), encoding="utf-8")
                shim.chmod(0o755)
                receipt_dir = Path(directory) / "receipts"
                with mock.patch.dict(
                    os.environ,
                    {"PATH": directory + os.pathsep + os.environ.get("PATH", "")},
                ):
                    result = run_experiment("HERESY-002", receipt_dir)

                self.assertNotEqual(result, 0)
                receipt = json.loads(
                    (receipt_dir / "HERESY-002.json").read_text(encoding="utf-8")
                )
                self.assertEqual(receipt["status"], "failed")
                self.assertNotEqual(receipt["exit_code"], 0)
                claims = receipt["observations"]["claims"]
                self.assertEqual(claims["heredoc_occupies_python_stdin"], "not_tested")
                self.assertEqual(claims["pipe_writer_can_receive_sigpipe"], "not_tested")
                self.assertEqual(claims["command_string_preserves_pipe_stdin"], "not_tested")
                self.assertEqual(
                    receipt["observations"]["observations"]["consumer_exit_code"],
                    child_exit,
                )
                with self.assertRaises(ExperimentError):
                    verify_experiment("HERESY-002", receipt_dir, quiet=True)

    def test_sqlite_file_copy_and_backup(self):
        receipt, _ = self.run_and_read("HERESY-003")
        observations = receipt["observations"]["observations"]
        self.assertEqual(observations["copied_integrity_check"], "ok")
        self.assertNotEqual(observations["copied_rows"], [["committed-in-wal"]])
        self.assertEqual(observations["backup_rows"], [["committed-in-wal"]])
        self.assertEqual(observations["backup_integrity_check"], "ok")

    def test_line_ending_normalization_and_unverified_windows_claim(self):
        receipt, _ = self.run_and_read("HERESY-004")
        observations = receipt["observations"]["observations"]
        self.assertTrue(observations["naive_contains_crcrlf"])
        self.assertTrue(observations["normalization_idempotent"])
        self.assertEqual(observations["cmd_exe_status"], "not_tested: this experiment ran on Linux")
        self.assertEqual(
            receipt["observations"]["claims"]["cmd_exe_interpretation"],
            "not_tested",
        )

    def test_receipt_hash_verifies_and_detects_tampering(self):
        _, receipt_directory = self.run_and_read("HERESY-001")
        self.assertEqual(verify_experiment("HERESY-001", receipt_directory, quiet=True), 0)
        receipt_path = Path(receipt_directory) / "HERESY-001.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["evidence"][0]["sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(ExperimentError):
            verify_experiment("HERESY-001", receipt_directory, quiet=True)

    def test_receipt_verification_rejects_malformed_timestamp(self):
        _, receipt_directory = self.run_and_read("HERESY-001")
        receipt_path = Path(receipt_directory) / "HERESY-001.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["generated_at"] = "not-a-timestamp"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(ExperimentError):
            verify_experiment("HERESY-001", receipt_directory, quiet=True)

    def test_placeholders_are_listed_but_not_runnable(self):
        ids = {item["id"] for item in discover_experiments()}
        self.assertTrue({"HERESY-005", "HERESY-006", "HERESY-007"}.issubset(ids))
        with self.assertRaises(ExperimentError):
            run_experiment("HERESY-005", tempfile.gettempdir())


if __name__ == "__main__":
    unittest.main()
