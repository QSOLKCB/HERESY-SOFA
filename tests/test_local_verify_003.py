"""Repository regression coverage for the LOCAL-VERIFY-003 archive."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "evidence/LOCAL-VERIFY-003/RUNNER/validate.py"
EXECUTE = REPOSITORY / "evidence/LOCAL-VERIFY-003/RUNNER/execute.py"
BUILD_REPORTS = REPOSITORY / "evidence/LOCAL-VERIFY-003/RUNNER/build_reports.py"
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module("local_verify_003_validator", VALIDATOR)
EXECUTE_MODULE = load_module("local_verify_003_execute", EXECUTE)
BUILD_MODULE = load_module("local_verify_003_build_reports", BUILD_REPORTS)


class LocalVerify003ArchiveTests(MODULE.LocalVerify003Tests):
    """Run the evidence-owned validation contract in repository CI."""

    def test_reproduction_runner_does_not_mutate_frozen_archive(self) -> None:
        archive_root = REPOSITORY / "evidence/LOCAL-VERIFY-003"
        before = {
            path.relative_to(archive_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in archive_root.rglob("*")
            if path.is_file()
        }
        canonical_text = (archive_root / "RAW/OFFLINE-RESULT.json").read_text(encoding="utf-8")
        canonical_digest = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

        def fake_run(index: int, environment: dict[str, str]) -> dict[str, object]:
            self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
            return {
                "run": index,
                "command": EXECUTE_MODULE.COMMAND,
                "cwd": "$REPOSITORY",
                "started_at_utc": "2026-11-05T00:00:00Z",
                "finished_at_utc": "2026-11-05T00:00:01Z",
                "elapsed_ns": 1,
                "exit_code": 0,
                "stdout": canonical_text,
                "stderr": "",
                "stdout_sha256": canonical_digest,
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            }

        with tempfile.TemporaryDirectory(prefix="local-verify-003-test-") as temporary:
            output = Path(temporary) / "reproduction"
            inventory = {"SOURCE/reference_oracle.py": {"bytes": 1, "sha256": "fixture"}}
            with (
                mock.patch.object(EXECUTE_MODULE.shutil, "which", return_value=sys.executable),
                mock.patch.object(EXECUTE_MODULE, "run_once", side_effect=fake_run),
                mock.patch.object(EXECUTE_MODULE, "source_inventory", return_value=inventory),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = EXECUTE_MODULE.main(["--output-dir", str(output)])
            self.assertEqual(exit_code, 0)
            receipt = json.loads((output / "OFFLINE-EXECUTION.json").read_text(encoding="utf-8"))
            self.assertTrue(receipt["successful"])
            self.assertTrue(receipt["archive_comparison"]["all_run_stdout_byte_identical_to_canonical"])
            self.assertTrue(receipt["archive_comparison"]["all_parsed_results_semantically_identical_to_canonical"])
            self.assertEqual(
                json.loads((output / "OFFLINE-RESULT.json").read_text(encoding="utf-8")),
                json.loads(canonical_text),
            )

        after = {
            path.relative_to(archive_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in archive_root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            EXECUTE_MODULE.prepare_output_directory(archive_root / "RAW")

    def test_report_builder_rejects_failed_inputs_before_writing(self) -> None:
        archive_root = REPOSITORY / "evidence/LOCAL-VERIFY-003"
        generated = (
            "ORACLE-MATRIX.csv",
            "CLAIM-LEDGER.csv",
            "NEGATIVE-CONTROLS.json",
            "REPORT.json",
            "REVIEW.md",
            "OPEN-ISSUES.md",
            "README.md",
        )

        def exercise(*, contradictory_only: bool) -> None:
            with tempfile.TemporaryDirectory(prefix="local-verify-003-build-test-") as temporary:
                copied = Path(temporary) / "LOCAL-VERIFY-003"
                shutil.copytree(archive_root, copied)
                result_path = copied / "RAW/OFFLINE-RESULT.json"
                execution_path = copied / "RAW/OFFLINE-EXECUTION.json"
                result = json.loads(result_path.read_text(encoding="utf-8"))
                execution = json.loads(execution_path.read_text(encoding="utf-8"))
                result["broken_controls"]["controls"][0]["passed"] = False
                if not contradictory_only:
                    failure = {
                        "id": "B001.first_auto_translation_detected",
                        "negative_control": True,
                        "passed": False,
                        "actual": False,
                        "expected": True,
                    }
                    result["assertions"]["failed_count"] = 1
                    result["assertions"]["failures"] = [failure]
                    execution["successful"] = False
                serialized = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
                digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
                for run in execution["runs"]:
                    run["stdout"] = serialized
                    run["stdout_sha256"] = digest
                    if not contradictory_only:
                        run["exit_code"] = 1
                result_path.write_text(serialized, encoding="utf-8")
                execution_path.write_text(
                    json.dumps(execution, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                before = {name: (copied / name).read_bytes() for name in generated}
                original_root = BUILD_MODULE.ROOT
                BUILD_MODULE.ROOT = copied
                try:
                    with self.assertRaisesRegex(
                        BUILD_MODULE.InvalidExecutionEvidence,
                        "failed or inconsistent evidence",
                    ):
                        BUILD_MODULE.main()
                finally:
                    BUILD_MODULE.ROOT = original_root
                after = {name: (copied / name).read_bytes() for name in generated}
                self.assertEqual(after, before)

        with self.subTest("contradictory failed control"):
            exercise(contradictory_only=True)
        with self.subTest("failed rerun"):
            exercise(contradictory_only=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
