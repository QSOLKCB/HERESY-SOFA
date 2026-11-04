#!/usr/bin/env python3
"""Bounded, opt-in CUDA device-assert experiment and sanitized report writer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "HERESY-005"
ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
SOURCE_FILES = ("experiment.json", "experiment.md", "run.py", "assertion.cu")
EVIDENCE_PATHS = tuple(EXPERIMENT_DIR / name for name in SOURCE_FILES) + (
    ROOT / "tests" / "test_heresy005.py",
)
CUDA_ERROR_ASSERT = 710
FAULT_OBSERVED_EXIT = 10
DEFAULT_REPEATS = 2
MAX_REPEATS = 5
COMMAND_TIMEOUT_SECONDS = 8.0
CLAIMS = (
    "device_assert_reported_as_cudaErrorAssert_710",
    "device_assert_can_surface_at_synchronization",
    "post_assert_context_rejects_further_work",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_revision() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=3, check=True,
        ).stdout.strip()
        evidence_arguments = [str(path.relative_to(ROOT)) for path in EVIDENCE_PATHS]
        dirty = bool(subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all", "--"] + evidence_arguments,
            capture_output=True, text=True, timeout=3, check=True,
        ).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return {"git_commit": None, "evidence_tree_dirty": None}
    return {"git_commit": commit, "evidence_tree_dirty": dirty}


def _evidence_hashes() -> list[dict[str, str]]:
    return [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
        }
        for path in EVIDENCE_PATHS
    ]


def _os_release() -> str:
    try:
        values = {}
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
        return values.get("PRETTY_NAME", platform.system())
    except OSError:
        return platform.system()


def _sanitize(text: str, replacements: tuple[tuple[str, str], ...]) -> str:
    result = text
    for raw, replacement in replacements:
        if raw:
            result = result.replace(raw, replacement)
    # CUDA diagnostics should use the copied basename.  This final guard keeps
    # an unexpected POSIX absolute path out of a portable public report.
    result = re.sub(r"(?<![A-Za-z0-9_.-])/(?:[^\s:'\"]+/)+([^\s:'\"]+)", r"<absolute-path>/\1", result)
    return result


def _command_record(command: list[str], replacements: tuple[tuple[str, str], ...]) -> list[str]:
    return [_sanitize(part, replacements) for part in command]


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None,
    timeout: float,
    replacements: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": _command_record(command, replacements),
            "exit_code": completed.returncode,
            "timed_out": False,
            "stdout": _sanitize(completed.stdout, replacements),
            "stderr": _sanitize(completed.stderr, replacements),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode("utf-8", "replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode("utf-8", "replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
        return {
            "command": _command_record(command, replacements),
            "exit_code": 124,
            "timed_out": True,
            "stdout": _sanitize(stdout, replacements),
            "stderr": _sanitize(stderr, replacements),
        }
    except OSError as error:
        return {
            "command": _command_record(command, replacements),
            "exit_code": 127,
            "timed_out": False,
            "stdout": "",
            "stderr": type(error).__name__ + ": command unavailable",
        }


def _json_stdout(record: dict[str, Any]) -> dict[str, Any] | None:
    try:
        value = json.loads(record["stdout"])
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def validate_trial(mode: str, record: dict[str, Any]) -> tuple[bool, str]:
    """Fail closed unless a child produced the exact expected observation."""
    if record.get("timed_out"):
        return False, "child timed out"
    observation = record.get("observation")
    if not isinstance(observation, dict) or observation.get("mode") != mode:
        return False, "missing or mismatched JSON observation"
    launch = observation.get("launch_status")
    synchronize = observation.get("synchronize_status")
    if mode == "control":
        valid = record.get("exit_code") == 0 and launch == 0 and synchronize == 0
        return valid, "control must launch and synchronize successfully"
    asserted = launch == CUDA_ERROR_ASSERT or synchronize == CUDA_ERROR_ASSERT
    valid = record.get("exit_code") == FAULT_OBSERVED_EXIT and asserted
    return valid, "fault must exit 10 and report cudaErrorAssert (710)"


def _base_report(command: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "title": "The CUDA Apparition",
        "generated_at": _utc_now(),
        "source_revision": _source_revision(),
        "runtime": {
            "python": platform.python_version(),
            "os": _os_release(),
            "kernel": platform.release(),
            "machine": platform.machine(),
        },
        "invocation": command,
        "commands": [],
        "child_exit_codes": [],
        "expected": {
            "control": "launch status 0, synchronization status 0, child exit 0",
            "fault": "exactly one device assert; cudaErrorAssert (710) at launch-status query or synchronization; child exit 10",
            "safety": "no CUDA call after observing cudaErrorAssert; parent timeout terminates a stuck child",
        },
        "actual": {},
        "evidence": _evidence_hashes(),
        "claims": {claim: "not_tested" for claim in CLAIMS},
        "limitations": [
            "No out-of-bounds write, reset, driver manipulation, stress loop, or persistent kernel is used.",
            "Continued CUDA work after a device assert is deliberately not attempted; context poisoning remains not_tested by this experiment.",
            "One workstation cannot establish behavior for other GPUs, drivers, runtimes, or toolchains.",
        ],
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _not_run(report: dict[str, Any], output: Path, reason: str, exit_code: int = 3) -> int:
    report["run_status"] = "NOT_RUN"
    report["conclusion"] = "UNCONFIRMED"
    report["actual"] = {"reason": reason}
    report["claims"] = {claim: "not_tested" for claim in CLAIMS}
    _write_report(output, report)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "run_status": "NOT_RUN", "report": output.name}, sort_keys=True))
    return exit_code


def run_hardware(args: argparse.Namespace) -> int:
    report = _base_report(["python3", "experiments/HERESY-005/run.py", "--hardware", "--output", args.output.name, "--repeats", str(args.repeats)])
    nvcc = shutil.which(args.nvcc) if os.sep not in args.nvcc else (args.nvcc if Path(args.nvcc).is_file() else None)
    if nvcc is None:
        return _not_run(report, args.output, "nvcc compiler unavailable")

    with tempfile.TemporaryDirectory(prefix="heresy005-") as directory:
        temporary = Path(directory)
        copied_source = temporary / "assertion.cu"
        binary = temporary / "assertion"
        shutil.copyfile(EXPERIMENT_DIR / "assertion.cu", copied_source)
        replacements = (
            (str(ROOT), "<repository>"),
            (str(temporary), "<temporary>"),
            (nvcc, "nvcc"),
        )
        base_env = os.environ.copy()
        base_env.pop("CUDA_LAUNCH_BLOCKING", None)

        tool_commands = [
            ([nvcc, "--version"], EXPERIMENT_DIR),
            (["nvidia-smi", "--query-gpu=name,driver_version,compute_cap", "--format=csv,noheader"], EXPERIMENT_DIR),
            ([nvcc, "--list-gpu-code"], EXPERIMENT_DIR),
        ]
        tool_records = []
        for command, cwd in tool_commands:
            tool_records.append(_run_command(
                command, cwd=cwd, env=base_env, timeout=COMMAND_TIMEOUT_SECONDS,
                replacements=replacements,
            ))
        report["commands"].extend(tool_records)
        report["runtime"].update({
            "nvcc_version_output": tool_records[0]["stdout"].strip(),
            "nvidia_smi_output": tool_records[1]["stdout"].strip(),
            "nvcc_supported_gpu_code": tool_records[2]["stdout"].splitlines(),
        })

        compile_record = _run_command(
            [nvcc, "-std=c++17", "-lineinfo", "assertion.cu", "-o", "assertion"],
            cwd=temporary, env=base_env, timeout=COMMAND_TIMEOUT_SECONDS,
            replacements=replacements,
        )
        report["commands"].append(compile_record)
        if compile_record["timed_out"] or compile_record["exit_code"] != 0 or not binary.is_file():
            return _not_run(report, args.output, "CUDA source did not compile")

        probe_record = _run_command(
            [str(binary), "--probe"], cwd=temporary, env=base_env,
            timeout=COMMAND_TIMEOUT_SECONDS, replacements=replacements,
        )
        probe_record["observation"] = _json_stdout(probe_record)
        report["commands"].append(probe_record)
        report["child_exit_codes"].append({"role": "device_probe", "exit_code": probe_record["exit_code"], "timed_out": probe_record["timed_out"]})
        probe = probe_record["observation"]
        if isinstance(probe, dict):
            report["runtime"].update({
                "cuda_driver_version": probe.get("driver_version"),
                "cuda_runtime_version": probe.get("runtime_version"),
                "gpu_model": probe.get("gpu_name"),
                "compute_capability": probe.get("compute_capability"),
                "device_count": probe.get("device_count"),
            })
        if probe_record["timed_out"] or probe_record["exit_code"] != 0 or not isinstance(probe, dict):
            return _not_run(report, args.output, "no working NVIDIA CUDA device/driver was available to the compiled probe")

        trials = []
        for launch_blocking in (False, True):
            for repeat in range(args.repeats):
                for mode in ("control", "fault"):
                    child_env = base_env.copy()
                    if launch_blocking:
                        child_env["CUDA_LAUNCH_BLOCKING"] = "1"
                    else:
                        child_env.pop("CUDA_LAUNCH_BLOCKING", None)
                    child = _run_command(
                        [str(binary), "--mode", mode], cwd=temporary,
                        env=child_env, timeout=args.timeout,
                        replacements=replacements,
                    )
                    child["observation"] = _json_stdout(child)
                    valid, validation = validate_trial(mode, child)
                    trial = {
                        "launch_behavior": "CUDA_LAUNCH_BLOCKING=1" if launch_blocking else "default",
                        "repeat": repeat,
                        "mode": mode,
                        "command": child["command"],
                        "exit_code": child["exit_code"],
                        "timed_out": child["timed_out"],
                        "stderr": child["stderr"],
                        "observation": child["observation"],
                        "accepted": valid,
                        "validation": validation,
                    }
                    trials.append(trial)
                    report["child_exit_codes"].append({
                        "role": mode,
                        "launch_behavior": trial["launch_behavior"],
                        "repeat": repeat,
                        "exit_code": child["exit_code"],
                        "timed_out": child["timed_out"],
                    })

        all_valid = all(trial["accepted"] for trial in trials)
        assertion_trials = [trial for trial in trials if trial["mode"] == "fault"]
        surfaced_at_sync = any(
            trial["observation"] and trial["observation"].get("synchronize_status") == CUDA_ERROR_ASSERT
            for trial in assertion_trials
        )
        report["actual"] = {
            "device_probe": probe,
            "nvcc_version_output": tool_records[0]["stdout"],
            "nvidia_smi_output": tool_records[1]["stdout"],
            "nvcc_supported_gpu_code": tool_records[2]["stdout"].splitlines(),
            "trials": trials,
            "all_required_observations_accepted": all_valid,
            "fault_reported_as_710": all(
                trial["observation"] and CUDA_ERROR_ASSERT in (
                    trial["observation"].get("launch_status"),
                    trial["observation"].get("synchronize_status"),
                )
                for trial in assertion_trials
            ),
            "observed_at_synchronization_in_at_least_one_trial": surfaced_at_sync,
        }
        report["claims"][CLAIMS[0]] = "executed" if all_valid else "unsupported"
        report["claims"][CLAIMS[1]] = "executed" if all_valid and surfaced_at_sync else "unsupported"
        report["claims"][CLAIMS[2]] = "not_tested"
        report["run_status"] = "PASS" if all_valid else "FAIL"
        report["conclusion"] = "CONFIRMED" if all_valid and surfaced_at_sync else "UNCONFIRMED"
        _write_report(args.output, report)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "run_status": report["run_status"], "report": args.output.name}, sort_keys=True))
        return 0 if all_valid else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hardware", action="store_true", help="explicitly opt in to the real CUDA execution")
    parser.add_argument("--output", type=Path, default=Path("HERESY-005-report.json"))
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--timeout", type=float, default=COMMAND_TIMEOUT_SECONDS)
    parser.add_argument("--nvcc", default="nvcc", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.hardware:
        parser.error("real GPU execution requires the explicit --hardware opt-in")
    if not 1 <= args.repeats <= MAX_REPEATS:
        parser.error("--repeats must be between 1 and {}".format(MAX_REPEATS))
    if not 0.1 <= args.timeout <= 30:
        parser.error("--timeout must be between 0.1 and 30 seconds")
    return run_hardware(args)


if __name__ == "__main__":
    raise SystemExit(main())
