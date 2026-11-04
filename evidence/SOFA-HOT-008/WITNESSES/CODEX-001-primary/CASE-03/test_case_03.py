#!/usr/bin/env python3
import argparse
import importlib.metadata
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import corrected_factory
import corrected_required
import original_posted
import targeted_ignore

SEED = 26051108


def run(command, cwd):
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {"command": command, "exit_code": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parent
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    parameterized = original_posted.myclass[original_posted.C2]()
    check("smallest_runtime_counterexample_exact_type",
          type(parameterized.var).__name__, "C")
    check("myclass_C2_does_not_contain_C2",
          isinstance(parameterized.var, original_posted.C2), False)
    check("subclass_override_contains_C2",
          isinstance(original_posted.myclass_child().var, original_posted.C2), True)
    check("targeted_ignore_remains_runtime_unsound",
          isinstance(targeted_ignore.claims_c2.var, targeted_ignore.C2), False)
    check("required_design_contains_C2",
          isinstance(corrected_required.claims_c2.var, corrected_required.C2), True)
    check("explicit_factory_design_contains_C2",
          isinstance(corrected_factory.claims_c2.var, corrected_factory.C2), True)
    missing_raises = False
    try:
        corrected_required.MyClass()
    except TypeError:
        missing_raises = True
    check("required_design_rejects_missing_value", missing_raises, True)

    mypy_runs = []
    mypy_path = shutil.which("mypy")
    if mypy_path:
        version_run = run([mypy_path, "--version"], root)
        original_run = run([mypy_path, "--show-error-codes", "original_posted.py"], root)
        unignored_run = run([mypy_path, "--show-error-codes", "unignored.py"], root)
        ignored_run = run([mypy_path, "--strict", "--show-error-codes", "targeted_ignore.py"], root)
        required_run = run([mypy_path, "--strict", "--show-error-codes", "corrected_required.py"], root)
        factory_run = run([mypy_path, "--strict", "--show-error-codes", "corrected_factory.py"], root)
        mypy_runs = [version_run, original_run, unignored_run, ignored_run, required_run, factory_run]
        check("posted_snippet_needs_bare_instance_annotation", original_run["exit_code"] != 0, True)
        check("installed_mypy_reports_unignored_factory_mismatch",
              "[assignment]" in unignored_run["stdout"], True)
        check("targeted_current_ignore_passes_mypy", ignored_run["exit_code"], 0)
        check("required_design_passes_strict_mypy", required_run["exit_code"], 0)
        check("explicit_factory_passes_strict_mypy", factory_run["exit_code"], 0)
        mypy_classification = "EXECUTED"
        mypy_version = importlib.metadata.version("mypy")
    else:
        mypy_classification = "NOT_TESTED"
        mypy_version = None

    passed = all(item["passed"] for item in checks)
    receipt = {
        "case": "CASE-03",
        "source_id": "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
        "source_author": "midhun-hermes",
        "reply_id": "368bb31d-b705-4870-adab-597533bf1cd5",
        "reply_author": "Nincompoop",
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_03.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "mypy": {"classification": mypy_classification, "version": mypy_version,
                  "runs": mypy_runs},
        "checks": checks,
        "conclusion": {
            "classification": "CONFIRMED_DEFECT",
            "defect": "myclass[C2]() constructs C, not C2. The lambda does not become a CT factory; an ignore only hides the mismatch.",
            "minimal_correction": "Make var required, or require a Callable[[], CT] in an explicit constructor/factory."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-03", "passed": passed, "checks": len(checks),
                      "mypy": mypy_version}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
