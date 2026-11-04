#!/usr/bin/env python3
"""HERESY-005 CUDA Cup report intake: structural screening, NEVER hardware proof.

No CUDA calls, external network, package dependencies, or publication actions.
A syntactically valid report remains self-reported until independent review.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

COMPETITION_ID = "HERESY-005-CUDA-CUP"
MAX_REPORT_BYTES = 2_000_000
MAX_REPEATS = 5
CUDA_ERROR_ASSERT = 710
REQUIRED_EVIDENCE = frozenset({
    "experiments/HERESY-005/experiment.json",
    "experiments/HERESY-005/experiment.md",
    "experiments/HERESY-005/run.py",
    "experiments/HERESY-005/assertion.cu",
    "tests/test_heresy005.py",
})
CLAIM_710 = "device_assert_reported_as_cudaErrorAssert_710"
CLAIM_SYNC = "device_assert_can_surface_at_synchronization"
CLAIM_CONTEXT = "post_assert_context_rejects_further_work"


def _integer(value: Any) -> bool:
    return type(value) is int


def screen(report: Any) -> dict[str, Any]:
    """Screen *structure* only. Never assign a hardware-verified verdict."""
    errors: list[str] = []

    def require(ok: bool, label: str) -> None:
        if not ok:
            errors.append(label)

    if not isinstance(report, dict):
        return {
            "competition_id": COMPETITION_ID, "screening": "REJECTED",
            "verified_hardware": False, "errors": ["report must be a JSON object"],
        }

    require(report.get("experiment_id") == "HERESY-005", "incorrect experiment ID")
    require(report.get("schema_version") == 1, "incorrect report schema")

    revision = report.get("source_revision")
    if not isinstance(revision, dict):
        revision = {}
    sha = revision.get("git_commit")
    require(
        isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha) is not None,
        "missing or malformed source commit",
    )
    require(revision.get("evidence_tree_dirty") is False, "evidence source must be clean")

    evidence = report.get("evidence")
    if isinstance(evidence, list):
        hashes: dict[str, str] = {}
        for item in evidence:
            if not isinstance(item, dict):
                errors.append("malformed evidence entry")
                continue
            path, digest = item.get("path"), item.get("sha256")
            if (
                not isinstance(path, str) or path not in REQUIRED_EVIDENCE
                or path in hashes or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                errors.append("invalid evidence path, digest, or duplicate")
                continue
            hashes[path] = digest
        require(set(hashes) == REQUIRED_EVIDENCE, "missing required source hashes")
    else:
        errors.append("missing source-hash evidence")

    claims = report.get("claims")
    if not isinstance(claims, dict):
        claims = {}
        errors.append("missing claims classification")
    require(claims.get(CLAIM_CONTEXT) == "not_tested", "post-assert context must remain not_tested")

    status = report.get("run_status")
    actual = report.get("actual")
    if not isinstance(actual, dict):
        actual = {}
        errors.append("missing actual results")

    # A compile-only result is valuable negative evidence, not a GPU win.
    if status == "NOT_RUN":
        require(report.get("conclusion") == "UNCONFIRMED", "NOT_RUN must be UNCONFIRMED")
        require(
            all(claims.get(key) == "not_tested" for key in (CLAIM_710, CLAIM_SYNC)),
            "NOT_RUN cannot claim assertion execution",
        )
        require(isinstance(actual.get("reason"), str) and bool(actual["reason"]),
                "NOT_RUN requires a reason")
        require(not actual.get("trials"), "NOT_RUN must not advertise trial results")
        result = "PREFLIGHT_ONLY"
    elif status == "PASS":
        result = "CANDIDATE_FOR_HUMAN_REVIEW"
        invocation = report.get("invocation")
        if not isinstance(invocation, list) or not all(isinstance(s, str) for s in invocation):
            invocation = []
            errors.append("malformed invocation")
        require("--hardware" in invocation, "missing explicit hardware opt-in")
        try:
            repeats = int(invocation[invocation.index("--repeats") + 1])
        except (ValueError, IndexError):
            repeats = -1
        require(1 <= repeats <= MAX_REPEATS, "repeats outside bounded range")

        runtime = report.get("runtime")
        if not isinstance(runtime, dict):
            runtime = {}
        device_count = runtime.get("device_count")
        require(_integer(device_count) and device_count >= 1, "missing usable GPU count")
        require(isinstance(runtime.get("gpu_model"), str) and bool(runtime["gpu_model"].strip()),
                "missing GPU model")
        require(_integer(runtime.get("cuda_driver_version")), "missing driver version")
        require(_integer(runtime.get("cuda_runtime_version")), "missing runtime version")
        probe = actual.get("device_probe")
        if not isinstance(probe, dict):
            probe = {}
        require(_integer(probe.get("device_count_status")) and probe["device_count_status"] == 0
                and _integer(probe.get("device_count"))
                and probe["device_count"] >= 1, "device preflight did not pass")

        commands = report.get("commands")
        require(
            isinstance(commands, list) and any(
                isinstance(item, dict) and "assertion.cu" in item.get("command", [])
                and item.get("exit_code") == 0 and item.get("timed_out") is False
                for item in commands
            ),
            "missing successful compilation record",
        )

        trials = actual.get("trials")
        if not isinstance(trials, list):
            trials = []
            errors.append("missing child trials")
        require(len(trials) == 4 * repeats, "incorrect trial matrix size")
        observed: set[tuple[str, int, str]] = set()
        saw_sync = False
        for trial in trials:
            if not isinstance(trial, dict):
                errors.append("malformed trial")
                continue
            mode = trial.get("mode")
            repeat = trial.get("repeat")
            launch_mode = trial.get("launch_behavior")
            key = (str(launch_mode), repeat if _integer(repeat) else -1, str(mode))
            require(
                launch_mode in ("default", "CUDA_LAUNCH_BLOCKING=1")
                and _integer(repeat) and 0 <= repeat < repeats
                and mode in ("control", "fault"),
                "invalid trial identity",
            )
            require(key not in observed, "duplicate trial identity")
            observed.add(key)
            require(trial.get("timed_out") is False, "child timeout")
            require(trial.get("accepted") is True, "worker rejected trial")
            observation = trial.get("observation")
            if not isinstance(observation, dict):
                observation = {}
            require(observation.get("mode") == mode, "mismatched observed trial mode")
            launch = observation.get("launch_status")
            sync = observation.get("synchronize_status")
            if mode == "control":
                require(
                    _integer(trial.get("exit_code")) and trial["exit_code"] == 0
                    and _integer(launch) and launch == 0
                    and _integer(sync) and sync == 0,
                    "control must return launch 0, sync 0, and exit 0",
                )
            elif mode == "fault":
                require(
                    _integer(trial.get("exit_code")) and trial["exit_code"] == 10
                    and (
                        (_integer(launch) and launch == CUDA_ERROR_ASSERT)
                        or (_integer(sync) and sync == CUDA_ERROR_ASSERT)
                    ),
                    "fault must return exit 10 and exact error 710",
                )
                if sync == CUDA_ERROR_ASSERT:
                    saw_sync = True
                if launch == CUDA_ERROR_ASSERT:
                    require(sync is None, "do not run synchronization after launch 710")
        expected = {
            (mode, index, role)
            for mode in ("default", "CUDA_LAUNCH_BLOCKING=1")
            for index in range(max(0, repeats))
            for role in ("control", "fault")
        }
        require(observed == expected, "incomplete launch-mode/repeat/role matrix")
        require(actual.get("all_required_observations_accepted") is True,
                "top-level success flag missing")
        require(actual.get("fault_reported_as_710") is True, "fault 710 flag missing")
        require(actual.get("observed_at_synchronization_in_at_least_one_trial") is saw_sync,
                "reported synchronization site disagrees with observations")
        require(report.get("conclusion") == ("CONFIRMED" if saw_sync else "UNCONFIRMED"),
                "conclusion does not match synchronization observations")
        require(claims.get(CLAIM_710) == "executed", "fault claim must be executed")
        require(claims.get(CLAIM_SYNC) == ("executed" if saw_sync else "unsupported"),
                "synchronization claim does not match observations")
    else:
        errors.append("only bounded PASS or NOT_RUN reports may enter screening")
        result = "REJECTED"

    if errors:
        result = "REJECTED"
    return {
        "competition_id": COMPETITION_ID,
        "screening": result,
        "verified_hardware": False,
        "errors": errors,
        "note": (
            "Structural self-report screening only. A GPU win requires human and "
            "independent evidence review; no rankings or scores are assigned."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="local sanitized HERESY-005 JSON report")
    args = parser.parse_args(argv)
    try:
        if args.report.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("report exceeds 2 MB bound")
        report = json.loads(args.report.read_text(encoding="utf-8"))
        result = screen(report)
    except (OSError, UnicodeError, ValueError):
        result = {
            "competition_id": COMPETITION_ID, "screening": "REJECTED",
            "verified_hardware": False, "errors": ["report unavailable, malformed or oversized"],
        }
    print(json.dumps(result, sort_keys=True))
    return 1 if result["screening"] == "REJECTED" else 0


if __name__ == "__main__":
    sys.exit(main())
