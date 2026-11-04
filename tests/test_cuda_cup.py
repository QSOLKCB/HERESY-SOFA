"""GPU-free validation of HERESY-005 competition intake and nonclaim boundaries."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUP = ROOT / "competitions" / "HERESY-005-CUDA-CUP"
SOURCE = ROOT / "experiments" / "HERESY-005"


def _load_screener():
    spec = importlib.util.spec_from_file_location("cuda_cup_screen", CUP / "screen.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("screener cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CudaCupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screener = _load_screener()
        cls.preflight = json.loads((SOURCE / "HERESY-005-report.json").read_text(encoding="utf-8"))

    def _synthetic_candidate(self):
        # This is FORGED TEST DATA, not executed CUDA evidence or a real entrant.
        report = copy.deepcopy(self.preflight)
        report["run_status"] = "PASS"
        report["conclusion"] = "CONFIRMED"
        report["runtime"]["gpu_model"] = "synthetic_gpu_not_hardware"
        report["runtime"]["device_count"] = 1
        report["runtime"]["compute_capability"] = "0.0"
        probe = {
            "driver_status": 0, "runtime_status": 0,
            "device_count_status": 0, "device_count": 1,
            "properties_status": 0,
            "driver_version": report["runtime"]["cuda_driver_version"],
            "runtime_version": report["runtime"]["cuda_runtime_version"],
            "gpu_name": report["runtime"]["gpu_model"],
            "compute_capability": report["runtime"]["compute_capability"],
        }
        probe_command = next(
            record for record in report["commands"] if "--probe" in record["command"]
        )
        probe_command.update(
            exit_code=0, timed_out=False,
            observation=copy.deepcopy(probe), stdout=json.dumps(probe),
        )
        report["actual"] = {
            "device_probe": probe,
            "all_required_observations_accepted": True,
            "fault_reported_as_710": True,
            "observed_at_synchronization_in_at_least_one_trial": True,
            "trials": [],
        }
        report["claims"]["device_assert_reported_as_cudaErrorAssert_710"] = "executed"
        report["claims"]["device_assert_can_surface_at_synchronization"] = "executed"
        for launch_mode in ("default", "CUDA_LAUNCH_BLOCKING=1"):
            for repeat in range(2):
                for mode in ("control", "fault"):
                    report["actual"]["trials"].append({
                        "launch_behavior": launch_mode, "repeat": repeat, "mode": mode,
                        "exit_code": 0 if mode == "control" else 10,
                        "timed_out": False, "accepted": True,
                        "observation": {
                            "mode": mode,
                            "launch_status": 0,
                            "synchronize_status": 0 if mode == "control" else 710,
                        },
                    })
        return report

    def test_historical_no_device_report_remains_preflight_only(self):
        screened = self.screener.screen(self.preflight)
        self.assertEqual(screened["screening"], "PREFLIGHT_ONLY")
        self.assertFalse(screened["verified_hardware"])
        self.assertEqual(screened["errors"], [])
        self.assertEqual(self.preflight["run_status"], "NOT_RUN")
        self.assertEqual(self.preflight["conclusion"], "UNCONFIRMED")

    def test_complete_synthetic_matrix_is_only_candidate_not_winner(self):
        screened = self.screener.screen(self._synthetic_candidate())
        self.assertEqual(screened["errors"], [])
        self.assertEqual(screened["screening"], "CANDIDATE_FOR_HUMAN_REVIEW")
        self.assertIs(screened["verified_hardware"], False)
        self.assertNotIn("score", screened)
        self.assertNotIn("winner", screened)

    def test_green_report_without_actual_children_rejected(self):
        forged = copy.deepcopy(self.preflight)
        forged["run_status"] = "PASS"
        forged["conclusion"] = "CONFIRMED"
        forged["claims"]["device_assert_reported_as_cudaErrorAssert_710"] = "executed"
        self.assertEqual(self.screener.screen(forged)["screening"], "REJECTED")

    def test_forged_child_error_or_control_not_a_710_witness(self):
        candidate = self._synthetic_candidate()
        for changes in (
            {"mode": "fault", "synchronize_status": 700},
            {"mode": "control", "synchronize_status": 710},
        ):
            with self.subTest(changes=changes):
                mutated = copy.deepcopy(candidate)
                record = next(
                    t for t in mutated["actual"]["trials"] if t["mode"] == changes["mode"]
                )
                record["observation"]["synchronize_status"] = changes["synchronize_status"]
                self.assertEqual(self.screener.screen(mutated)["screening"], "REJECTED")

    def test_missing_or_duplicate_trial_and_timeout_rejected(self):
        candidate = self._synthetic_candidate()
        for mutation in ("missing", "duplicate", "timeout"):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(candidate)
                if mutation == "missing":
                    bad["actual"]["trials"].pop()
                elif mutation == "duplicate":
                    bad["actual"]["trials"][-1] = copy.deepcopy(bad["actual"]["trials"][0])
                else:
                    bad["actual"]["trials"][0]["timed_out"] = True
                self.assertEqual(self.screener.screen(bad)["screening"], "REJECTED")

    def test_boolean_zero_cannot_fake_cuda_success(self):
        candidate = self._synthetic_candidate()
        for mutation in ("control_launch", "control_exit", "probe_status"):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(candidate)
                if mutation == "control_launch":
                    bad["actual"]["trials"][0]["observation"]["launch_status"] = False
                elif mutation == "control_exit":
                    bad["actual"]["trials"][0]["exit_code"] = False
                else:
                    bad["actual"]["device_probe"]["device_count_status"] = False
                self.assertEqual(self.screener.screen(bad)["screening"], "REJECTED")

    def test_extreme_or_invalid_repeats_fail_before_matrix_allocation(self):
        candidate = self._synthetic_candidate()
        for raw in ("1000000000000", "0", "-1", "six"):
            with self.subTest(raw_repeats=raw):
                bad = copy.deepcopy(candidate)
                index = bad["invocation"].index("--repeats") + 1
                bad["invocation"][index] = raw
                screened = self.screener.screen(bad)
                self.assertEqual(screened["screening"], "REJECTED")
                self.assertIn("repeats outside bounded range", screened["errors"])
                self.assertFalse(screened["verified_hardware"])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "huge-repeats.json"
            bad = copy.deepcopy(candidate)
            bad["invocation"][-1] = "1000000000000"
            path.write_text(json.dumps(bad), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CUP / "screen.py"), str(path)],
                capture_output=True, text=True, timeout=4, check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)["screening"], "REJECTED")
            self.assertNotIn("Traceback", result.stderr)

    def test_malformed_argv_yields_machine_readable_rejection(self):
        candidate = self._synthetic_candidate()
        for command in (None, 7, False, {"argv": []}, ["nvcc", None], ["nvcc", 123]):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as directory:
                bad = copy.deepcopy(candidate)
                compile_record = next(
                    item for item in bad["commands"]
                    if "assertion.cu" in item["command"]
                )
                compile_record["command"] = command
                path = Path(directory) / "malformed-argv.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(CUP / "screen.py"), str(path)],
                    capture_output=True, text=True, timeout=4, check=False,
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)["screening"], "REJECTED")
                self.assertNotIn("Traceback", result.stderr)

    def test_recorded_probe_must_succeed_and_match_probe_observation(self):
        candidate = self._synthetic_candidate()
        mutations = (
            "timeout", "exit_error", "reported_driver_error", "reported_runtime_error",
            "reported_properties_error", "observation_mismatch", "stdout_mismatch",
            "runtime_version_mismatch", "missing_probe",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(candidate)
                record = next(
                    item for item in bad["commands"] if "--probe" in item["command"]
                )
                if mutation == "timeout":
                    record["timed_out"] = True
                    record["exit_code"] = 124
                elif mutation == "exit_error":
                    record["exit_code"] = 31
                elif mutation == "reported_driver_error":
                    bad["actual"]["device_probe"]["driver_status"] = 1
                elif mutation == "reported_runtime_error":
                    bad["actual"]["device_probe"]["runtime_status"] = 1
                elif mutation == "reported_properties_error":
                    bad["actual"]["device_probe"]["properties_status"] = 1
                elif mutation == "observation_mismatch":
                    record["observation"]["device_count"] = 2
                elif mutation == "stdout_mismatch":
                    record["stdout"] = "{}"
                elif mutation == "runtime_version_mismatch":
                    bad["runtime"]["cuda_runtime_version"] += 1
                elif mutation == "missing_probe":
                    bad["commands"].remove(record)
                screened = self.screener.screen(bad)
                self.assertEqual(screened["screening"], "REJECTED")
                self.assertFalse(screened["verified_hardware"])
                self.assertTrue(screened["errors"])

    def test_deeply_nested_probe_stdout_is_machine_readable_rejection(self):
        # Reproduce the Codex P2: nested valid JSON under the 2 MB report cap.
        candidate = self._synthetic_candidate()
        for depth in (1100, 100000):
            with self.subTest(depth=depth), tempfile.TemporaryDirectory() as directory:
                bad = copy.deepcopy(candidate)
                probe = next(item for item in bad["commands"] if "--probe" in item["command"])
                probe["stdout"] = "[" * depth + "0" + "]" * depth
                path = Path(directory) / "nested-probe.json"
                path.write_text(json.dumps(bad), encoding="utf-8")
                self.assertLess(path.stat().st_size, self.screener.MAX_REPORT_BYTES)
                outcome = subprocess.run(
                    [sys.executable, str(CUP / "screen.py"), str(path)],
                    capture_output=True, text=True, timeout=4, check=False,
                )
                self.assertEqual(outcome.returncode, 1, outcome.stderr)
                response = json.loads(outcome.stdout)
                self.assertEqual(response["screening"], "REJECTED")
                self.assertFalse(response["verified_hardware"])
                self.assertIn(
                    "device probe stdout disagrees with recorded observation",
                    response["errors"],
                )
                self.assertNotIn("Traceback", outcome.stderr)

    def test_deeply_nested_outer_json_is_machine_readable_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested-report.json"
            path.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            outcome = subprocess.run(
                [sys.executable, str(CUP / "screen.py"), str(path)],
                capture_output=True, text=True, timeout=4, check=False,
            )
            self.assertEqual(outcome.returncode, 1, outcome.stderr)
            response = json.loads(outcome.stdout)
            self.assertEqual(response["screening"], "REJECTED")
            self.assertFalse(response["verified_hardware"])
            self.assertNotIn("Traceback", outcome.stderr)

    def test_post_assert_context_claim_rejected(self):
        bad = self._synthetic_candidate()
        bad["claims"]["post_assert_context_rejects_further_work"] = "executed"
        self.assertEqual(self.screener.screen(bad)["screening"], "REJECTED")

    def test_missing_source_identity_rejected(self):
        bad = self._synthetic_candidate()
        bad["evidence"][0]["sha256"] = "unsigned"
        self.assertEqual(self.screener.screen(bad)["screening"], "REJECTED")
        bad = self._synthetic_candidate()
        bad["source_revision"]["evidence_tree_dirty"] = True
        self.assertEqual(self.screener.screen(bad)["screening"], "REJECTED")

    def test_cli_accepts_preflight_and_rejects_forged_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            for payload, expected_status, code in (
                (self.preflight, "PREFLIGHT_ONLY", 0),
                (self._synthetic_candidate(), "CANDIDATE_FOR_HUMAN_REVIEW", 0),
                ({"run_status": "PASS"}, "REJECTED", 1),
            ):
                report.write_text(json.dumps(payload), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(CUP / "screen.py"), str(report)],
                    capture_output=True, text=True, timeout=4, check=False,
                )
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(json.loads(result.stdout)["screening"], expected_status)
            report.write_bytes(b"x" * (self.screener.MAX_REPORT_BYTES + 1))
            result = subprocess.run(
                [sys.executable, str(CUP / "screen.py"), str(report)],
                capture_output=True, text=True, timeout=4, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["screening"], "REJECTED")

    def test_competition_registry_and_corkboard_preserve_wanted_state(self):
        rules = json.loads((CUP / "rules.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "sofa/manifest.json").read_text(encoding="utf-8"))
        case = json.loads((ROOT / "site/cases.json").read_text(encoding="utf-8"))
        source = json.loads((SOURCE / "experiment.json").read_text(encoding="utf-8"))
        entries = [x for x in manifest.get("competitions", []) if x["id"] == rules["competition_id"]]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["sofa_question_id"], rules["sofa_question_id"])
        self.assertEqual(entries[0]["state"], "published")
        self.assertFalse(manifest["publishing_enabled"])
        self.assertEqual(rules["reference_outcome"], "NOT_RUN")
        self.assertEqual(rules["hardware_verdict"], "WANTED")
        self.assertEqual(rules["state"], "OPEN")
        self.assertIsNone(rules["current_winner"])
        self.assertEqual(rules["submitted_entries"], [])
        self.assertEqual(sum(rules["scoring_for_reviewed_hardware_only"].values()), 100)
        self.assertEqual(rules["hardware_gate"]["fault_error_code"], 710)
        self.assertEqual(source["status"], "placeholder")
        self.assertIsNone(source["entrypoint"])
        cuda_case = next(x for x in case["cases"] if x["id"] == "HERESY-005")
        self.assertEqual(cuda_case["status"], "placeholder")
        self.assertEqual(cuda_case["evidenceState"], "blocked")
        self.assertEqual(cuda_case["competition"], rules["competition_id"])
        html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        js = (ROOT / "site/app.js").read_text(encoding="utf-8")
        self.assertIn(rules["sofa_question_id"], js)
        self.assertIn("CUDA AGENT CUP", html)
        self.assertIn("JOIN THE CUDA ASSERTION COMPETITION", js)


if __name__ == "__main__":
    unittest.main()
