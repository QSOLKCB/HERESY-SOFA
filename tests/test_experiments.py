import json
import tempfile
import unittest
from pathlib import Path

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
