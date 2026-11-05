#!/usr/bin/env python3
"""Run the two missing LOCAL-VERIFY-002 checker matrices twice, offline."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
FROZEN_ROOT = REPOSITORY / "evidence/LOCAL-VERIFY-002"
FIXTURES = FROZEN_ROOT / "FIXTURES"
RAW = ROOT / "RAW"
SEED = 26051105

MYPY_EXPECTED_EXITS = {
    "GA01": 1,
    "GA02": 1,
    "GA03": 0,
    "GA04": 1,
    "GA05": 1,
    "GA06": 1,
    "DC01": 1,
    "DC02": 1,
    "DC03": 0,
    "DC04": 0,
    "DC05": 0,
    "DC06": 0,
    "DC07": 1,
    "NC01": 1,
}

MYPY_DIAGNOSTIC = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+)(?::(?P<column>\d+))?: "
    r"(?P<severity>error|warning|note): (?P<message>.*?)(?:  \[(?P<code>[^]]+)\])?$"
)


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(value: str, acquisition_root: Path) -> str:
    return (
        value.replace(str(REPOSITORY), "<REPOSITORY>")
        .replace(str(acquisition_root), "<ACQUISITION_ROOT>")
        .replace(str(Path.home()), "$HOME")
    )


def normalize_argv(argv: list[str], acquisition_root: Path) -> list[str]:
    return [normalize_text(value, acquisition_root) for value in argv]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(
    argv: list[str],
    *,
    label: str,
    acquisition_root: Path,
    timeout: int = 90,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update({
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": str(SEED),
        "UV_OFFLINE": "1",
        "NO_COLOR": "1",
    })
    started = utc_now()
    timed_out = False
    try:
        completed = subprocess.run(
            argv,
            cwd=REPOSITORY,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        exit_code: int | None = completed.returncode
        stdout_bytes = completed.stdout
        stderr_bytes = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout_bytes = exc.stdout or b""
        stderr_bytes = exc.stderr or b""
    finished = utc_now()
    stdout_decoded = stdout_bytes.decode("utf-8", errors="replace")
    stderr_decoded = stderr_bytes.decode("utf-8", errors="replace")
    return {
        "label": label,
        "argv": normalize_argv(argv, acquisition_root),
        "cwd": "<REPOSITORY>",
        "environment_overrides": {
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": str(SEED),
            "UV_OFFLINE": "1",
            "NO_COLOR": "1",
        },
        "started_at_utc": started,
        "finished_at_utc": finished,
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "stdout": normalize_text(stdout_decoded, acquisition_root),
        "stderr": normalize_text(stderr_decoded, acquisition_root),
        "raw_stdout_sha256": sha256_bytes(stdout_bytes),
        "raw_stderr_sha256": sha256_bytes(stderr_bytes),
    }


def parse_mypy(command: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for line in command["stdout"].splitlines():
        match = MYPY_DIAGNOSTIC.match(line)
        if not match:
            continue
        item = match.groupdict()
        diagnostics.append({
            "file": item["path"],
            "severity": item["severity"],
            "message": item["message"],
            "rule": item["code"],
            "range": {
                "start": {
                    "line": int(item["line"]),
                    "character": int(item["column"]) if item["column"] else None,
                }
            },
        })
    return diagnostics


def parse_pyright(command: dict[str, Any], acquisition_root: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(command["stdout"])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Pyright did not emit valid JSON for {command['label']}: {exc}") from exc
    diagnostics = parsed.get("generalDiagnostics", [])
    for item in diagnostics:
        item["file"] = normalize_text(item["file"], acquisition_root)
    return {
        "version": parsed.get("version"),
        "time": parsed.get("time"),
        "generalDiagnostics": diagnostics,
        "summary": parsed.get("summary", {}),
    }


def semantic_pyright(value: dict[str, Any]) -> dict[str, Any]:
    summary = value["parsed"]["summary"]
    return {
        "exit_code": value["exit_code"],
        "stderr": value["stderr"],
        "diagnostics": value["parsed"]["generalDiagnostics"],
        "summary": {
            "filesAnalyzed": summary.get("filesAnalyzed"),
            "errorCount": summary.get("errorCount"),
            "warningCount": summary.get("warningCount"),
            "informationCount": summary.get("informationCount"),
        },
    }


def semantic_mypy(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "exit_code": value["exit_code"],
        "stdout": value["stdout"],
        "stderr": value["stderr"],
        "diagnostics": value["diagnostics"],
    }


def fixture_inventory() -> list[dict[str, Any]]:
    source = load_json(FROZEN_ROOT / "RAW/fixture-inventory.json")
    inventory: list[dict[str, Any]] = []
    for item in source:
        path = FIXTURES / item["file"]
        actual = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        expected = {"bytes": item["bytes"], "sha256": item["sha256"]}
        if actual != expected:
            raise RuntimeError(f"frozen fixture changed: {item['id']}: {actual} != {expected}")
        inventory.append({
            **item,
            "source_path": f"evidence/LOCAL-VERIFY-002/FIXTURES/{item['file']}",
            "reused_without_copy": True,
        })
    return inventory


def tool_probe(
    args: argparse.Namespace, acquisition_root: Path
) -> dict[str, Any]:
    mypy_version = run_command(
        [str(args.mypy), "--version"],
        label="mypy-version",
        acquisition_root=acquisition_root,
    )
    pyright_version = run_command(
        [str(args.node), str(args.pyright_index), "--version"],
        label="pyright-version",
        acquisition_root=acquisition_root,
    )
    python_version = run_command(
        [str(args.python), "--version"],
        label="python-version",
        acquisition_root=acquisition_root,
    )
    node_version = run_command(
        [str(args.node), "--version"],
        label="node-version",
        acquisition_root=acquisition_root,
    )
    if mypy_version["exit_code"] != 0 or mypy_version["stdout"].strip() != "mypy 2.3.1 (compiled: yes)":
        raise RuntimeError(f"mypy version gate failed: {mypy_version}")
    if pyright_version["exit_code"] != 0 or pyright_version["stdout"].strip() != "pyright 1.1.414":
        raise RuntimeError(f"Pyright version gate failed: {pyright_version}")
    if python_version["exit_code"] != 0 or "Python 3.14.4" not in (
        python_version["stdout"] + python_version["stderr"]
    ):
        raise RuntimeError(f"Python version gate failed: {python_version}")
    if node_version["exit_code"] != 0 or node_version["stdout"].strip() != "v22.18.0":
        raise RuntimeError(f"Node version gate failed: {node_version}")
    return {
        "mypy": {
            "version": "2.3.1",
            "compiled": True,
            "executable": normalize_text(str(args.mypy.resolve()), acquisition_root),
            "executable_bytes": args.mypy.stat().st_size,
            "executable_sha256": sha256_file(args.mypy),
            "version_receipt": mypy_version,
        },
        "pyright": {
            "version": "1.1.414",
            "entrypoint": normalize_text(str(args.pyright_index.resolve()), acquisition_root),
            "entrypoint_bytes": args.pyright_index.stat().st_size,
            "entrypoint_sha256": sha256_file(args.pyright_index),
            "version_receipt": pyright_version,
        },
        "python": {
            "version": "3.14.4",
            "executable": normalize_text(str(args.python.resolve()), acquisition_root),
            "executable_bytes": args.python.stat().st_size,
            "executable_sha256": sha256_file(args.python),
            "version_receipt": python_version,
        },
        "node": {
            "version": "22.18.0",
            "executable": normalize_text(str(args.node.resolve()), acquisition_root),
            "executable_bytes": args.node.stat().st_size,
            "executable_sha256": sha256_file(args.node),
            "version_receipt": node_version,
        },
        "python_target": "3.14",
        "network_policy_during_execution": "offline; UV_OFFLINE=1; local executables and fixtures only",
    }


def execute_mypy(
    args: argparse.Namespace,
    fixtures: list[dict[str, Any]],
    acquisition_root: Path,
    mode: str,
    run_number: int,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for fixture in fixtures:
        fixture_path = Path("evidence/LOCAL-VERIFY-002/FIXTURES") / fixture["file"]
        argv = [
            str(args.mypy),
            "--python-version", "3.14",
            "--no-incremental",
            "--show-error-codes",
            "--show-column-numbers",
            "--no-pretty",
            "--no-color-output",
            "--no-error-summary",
        ]
        if mode == "strict":
            argv.append("--strict")
        argv.append(fixture_path.as_posix())
        command = run_command(
            argv,
            label=f"mypy-2.3.1-{mode}-run-{run_number}-{fixture['id']}",
            acquisition_root=acquisition_root,
        )
        command.update({
            "fixture_id": fixture["id"],
            "fixture_path": fixture["source_path"],
            "fixture_sha256": fixture["sha256"],
            "expected_exit_code_from_mypy_1_19_1": MYPY_EXPECTED_EXITS[fixture["id"]],
            "diagnostics": parse_mypy(command),
        })
        results.append(command)
    return {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "checker": "mypy",
        "version": "2.3.1",
        "mode": mode,
        "run_number": run_number,
        "python_target": "3.14",
        "fresh_process_per_fixture": True,
        "result_count": len(results),
        "results": results,
    }


def execute_pyright(
    args: argparse.Namespace,
    fixtures: list[dict[str, Any]],
    acquisition_root: Path,
    mode: str,
    run_number: int,
) -> dict[str, Any]:
    config = ROOT / "CONFIGS" / f"pyright-{mode}.json"
    results: list[dict[str, Any]] = []
    for fixture in fixtures:
        fixture_path = Path("evidence/LOCAL-VERIFY-002/FIXTURES") / fixture["file"]
        argv = [
            str(args.node),
            str(args.pyright_index),
            "--project", str(config),
            "--pythonversion", "3.14",
            "--pythonplatform", "Linux",
            "--outputjson",
            fixture_path.as_posix(),
        ]
        command = run_command(
            argv,
            label=f"pyright-1.1.414-{mode}-run-{run_number}-{fixture['id']}",
            acquisition_root=acquisition_root,
        )
        command.update({
            "fixture_id": fixture["id"],
            "fixture_path": fixture["source_path"],
            "fixture_sha256": fixture["sha256"],
            "config_path": f"CONFIGS/pyright-{mode}.json",
            "config_sha256": sha256_file(config),
            "parsed": parse_pyright(command, acquisition_root),
        })
        results.append(command)
    return {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "checker": "Pyright",
        "version": "1.1.414",
        "mode": mode,
        "run_number": run_number,
        "python_target": "3.14",
        "fresh_process_per_fixture": True,
        "result_count": len(results),
        "results": results,
    }


def pair_map(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["fixture_id"]: item for item in document["results"]}


def negative_controls(documents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for checker, mode, fixture_id, reason in [
        ("mypy", "default", "GA06", "ordinary Generic[T] excess arity"),
        ("mypy", "strict", "GA06", "ordinary Generic[T] excess arity"),
        ("pyright", "standard", "GA06", "ordinary Generic[T] excess arity"),
        ("pyright", "strict", "GA06", "ordinary Generic[T] excess arity"),
        ("mypy", "default", "NC01", "deliberately wrong assert_type"),
        ("mypy", "strict", "NC01", "deliberately wrong assert_type"),
        ("pyright", "standard", "NC01", "deliberately wrong assert_type"),
        ("pyright", "strict", "NC01", "deliberately wrong assert_type"),
        ("mypy", "default", "DC02", "unsuppressed bound-TypeVar factory mismatch"),
        ("mypy", "strict", "DC02", "unsuppressed bound-TypeVar factory mismatch"),
        ("pyright", "standard", "DC02", "unsuppressed bound-TypeVar factory mismatch"),
        ("pyright", "strict", "DC02", "unsuppressed bound-TypeVar factory mismatch"),
    ]:
        key = f"{checker}-{mode}-run-1"
        item = pair_map(documents[key])[fixture_id]
        controls.append({
            "checker": checker,
            "mode": mode,
            "fixture_id": fixture_id,
            "control": reason,
            "expected": "checker rejects with at least one error",
            "actual_exit_code": item["exit_code"],
            "error_diagnostic_count": sum(
                diagnostic["severity"] == "error"
                for diagnostic in (
                    item["diagnostics"] if checker == "mypy"
                    else item["parsed"]["generalDiagnostics"]
                )
            ),
            "passed": item["exit_code"] == 1,
        })
    return controls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mypy", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--node", required=True, type=Path)
    parser.add_argument("--pyright-index", required=True, type=Path)
    parser.add_argument("--acquisition-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    acquisition_root = args.acquisition_root.resolve()
    started = utc_now()
    fixtures = fixture_inventory()
    before = {item["id"]: sha256_file(FIXTURES / item["file"]) for item in fixtures}
    tools = tool_probe(args, acquisition_root)
    write_json(RAW / "tool-inventory.json", tools)
    write_json(RAW / "fixture-inventory.json", fixtures)

    documents: dict[str, dict[str, Any]] = {}
    for run_number in (1, 2):
        for mode in ("default", "strict"):
            key = f"mypy-{mode}-run-{run_number}"
            document = execute_mypy(args, fixtures, acquisition_root, mode, run_number)
            documents[key] = document
            write_json(RAW / f"mypy-2.3.1-{mode}-run-{run_number}.json", document)
        for mode in ("standard", "strict"):
            key = f"pyright-{mode}-run-{run_number}"
            document = execute_pyright(args, fixtures, acquisition_root, mode, run_number)
            documents[key] = document
            write_json(RAW / f"pyright-1.1.414-{mode}-run-{run_number}.json", document)

    after = {item["id"]: sha256_file(FIXTURES / item["file"]) for item in fixtures}
    pairs: list[dict[str, Any]] = []
    for checker, modes, semantic in [
        ("mypy", ("default", "strict"), semantic_mypy),
        ("pyright", ("standard", "strict"), semantic_pyright),
    ]:
        for mode in modes:
            first = pair_map(documents[f"{checker}-{mode}-run-1"])
            second = pair_map(documents[f"{checker}-{mode}-run-2"])
            for fixture in fixtures:
                fixture_id = fixture["id"]
                identical = semantic(first[fixture_id]) == semantic(second[fixture_id])
                pairs.append({
                    "checker": checker,
                    "mode": mode,
                    "fixture_id": fixture_id,
                    "semantic_output_identical": identical,
                    "raw_stdout_identical": (
                        first[fixture_id]["raw_stdout_sha256"]
                        == second[fixture_id]["raw_stdout_sha256"]
                    ),
                    "note": (
                        "Pyright embeds wall-clock and duration fields in JSON; semantic "
                        "comparison excludes only those two measurement fields."
                        if checker == "pyright" else "Exact normalized output comparison."
                    ),
                })
    controls = negative_controls(documents)
    timed_out = [
        item["label"]
        for document in documents.values()
        for item in document["results"]
        if item["timed_out"]
    ]
    execution = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "seed": SEED,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "fixture_count": len(fixtures),
        "matrix_rows": 56,
        "mypy_matrix_rows": 28,
        "pyright_matrix_rows": 28,
        "fresh_process_checker_commands": 112,
        "version_probe_commands": 4,
        "checker_timeouts": timed_out,
        "negative_control_count": len(controls),
        "failed_negative_control_count": sum(not item["passed"] for item in controls),
        "source_unchanged": before == after,
        "network_access_during_execution": False,
        "package_manager_invocations_during_execution": False,
        "all_semantic_repeat_pairs_identical": all(
            item["semantic_output_identical"] for item in pairs
        ),
    }
    determinism = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "all_semantic_repeat_pairs_identical": execution["all_semantic_repeat_pairs_identical"],
        "pairs": pairs,
    }
    write_json(RAW / "NEGATIVE-CONTROLS.json", {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "control_count": len(controls),
        "failed_control_count": execution["failed_negative_control_count"],
        "controls": controls,
    })
    write_json(RAW / "determinism.json", determinism)
    write_json(RAW / "EXECUTION.json", execution)

    failures = []
    if timed_out:
        failures.append(f"timeouts: {timed_out}")
    if before != after:
        failures.append("frozen fixture bytes changed")
    if execution["failed_negative_control_count"]:
        failures.append("one or more negative controls failed")
    if not execution["all_semantic_repeat_pairs_identical"]:
        failures.append("one or more repeat pairs differed semantically")
    print(json.dumps({**execution, "failures": failures}, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
