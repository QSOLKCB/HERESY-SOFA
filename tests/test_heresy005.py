"""HERESY-005 safety, isolation, and false-green regression tests."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "HERESY-005" / "run.py"
CUDA_SOURCE = ROOT / "experiments" / "HERESY-005" / "assertion.cu"


def load_runner():
    spec = importlib.util.spec_from_file_location("heresy005_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Heresy005Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def test_gpu_execution_requires_explicit_hardware_opt_in(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True,
            timeout=5, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--hardware", result.stderr)

    def test_missing_compiler_is_not_run_and_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--hardware", "--nvcc",
                 str(Path(directory) / "missing-nvcc"), "--output", str(report_path)],
                capture_output=True, text=True, timeout=8, check=False,
            )
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["run_status"], "NOT_RUN")
            self.assertEqual(report["conclusion"], "UNCONFIRMED")
            self.assertTrue(all(value == "not_tested" for value in report["claims"].values()))

    def test_exact_710_and_child_exit_are_required(self):
        good_control = {
            "exit_code": 0, "timed_out": False,
            "observation": {"mode": "control", "launch_status": 0, "synchronize_status": 0},
        }
        good_fault = {
            "exit_code": 10, "timed_out": False,
            "observation": {"mode": "fault", "launch_status": 0, "synchronize_status": 710},
        }
        self.assertTrue(self.runner.validate_trial("control", good_control)[0])
        self.assertTrue(self.runner.validate_trial("fault", good_fault)[0])

        for mutation in (
            dict(good_fault, exit_code=0),
            dict(good_fault, timed_out=True),
            dict(good_fault, observation={"mode": "fault", "launch_status": 0, "synchronize_status": 700}),
            dict(good_fault, observation=None),
        ):
            with self.subTest(mutation=mutation):
                self.assertFalse(self.runner.validate_trial("fault", mutation)[0])

    def test_parent_timeout_cannot_validate_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            record = self.runner._run_command(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                cwd=Path(directory), env=None, timeout=0.1, replacements=(),
            )
        record["observation"] = None
        self.assertTrue(record["timed_out"])
        self.assertEqual(record["exit_code"], 124)
        self.assertFalse(self.runner.validate_trial("fault", record)[0])

    def test_cuda_source_is_one_thread_and_has_no_poisoned_context_followup(self):
        source = CUDA_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(source.count("controlled_assertion<<<1, 1>>>("), 1)
        self.assertIn("assert(condition);", source)
        self.assertNotIn("cudaDeviceReset", source)
        self.assertNotIn("cudaMalloc", source)
        self.assertNotIn("cudaMemcpy", source)
        synchronization = source.index("cudaError_t synchronize_status = cudaDeviceSynchronize();")
        tail = source[synchronization:]
        self.assertEqual(tail.count("cudaDeviceSynchronize()"), 1)
        self.assertNotIn("cudaGetLastError()", tail)


if __name__ == "__main__":
    unittest.main()
