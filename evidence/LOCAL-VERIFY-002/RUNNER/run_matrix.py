#!/usr/bin/env python3
"""Execute LOCAL-VERIFY-002 with installed tools only and preserve raw output."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "FIXTURES"
RAW = ROOT / "RAW"
REPOSITORY = ROOT.parents[1]
HOME = Path.home()
SEED = 26051105

PYTHONS = {
    "3.14.4": Path("/usr/bin/python3.14"),
    "3.13.14": HOME / ".local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/bin/python3.13",
    "3.12.13": HOME / ".local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12",
    "3.11.15": HOME / ".local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11",
}

FIXTURE_SPECS = [
    {
        "id": "GA01",
        "file": "GA01-original-genericalias-reply.py",
        "subject": "verbatim GenericAlias reply",
        "provenance": "byte-identical copy of LOCAL-VERIFY-001/PYTHON-TYPING/generic_alias_verbatim.py",
        "runtime_exit": 1,
        "mypy_1_19_1_exit": 1,
        "expected": "CPython raises before class declaration; static checker rejects the subscript form.",
    },
    {
        "id": "GA02",
        "file": "GA02-types-genericalias-constructor.py",
        "subject": "types.GenericAlias(origin, args)",
        "provenance": "independent corrected fixture",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "Runtime constructor succeeds without enforcing element values; checker support is measured separately.",
    },
    {
        "id": "GA03",
        "file": "GA03-custom-class-getitem-source.py",
        "subject": "verbatim custom alias definition",
        "provenance": "verbatim code block from frozen GenericAlias TIL body",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 0,
        "expected": "Definitions alone are accepted; use-site behavior requires a separate fixture.",
    },
    {
        "id": "GA04",
        "file": "GA04-custom-class-getitem-use.py",
        "subject": "custom __class_getitem__ use",
        "provenance": "independent use-site fixture",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "Runtime hook intercepts the subscript; static generic checks reject literal ellipsis and excess arguments.",
    },
    {
        "id": "GA05",
        "file": "GA05-typevartuple-ellipsis.py",
        "subject": "Generic[*Ts] literal ellipsis",
        "provenance": "independent runtime/static boundary fixture",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "CPython accepts ellipsis as runtime metadata; mypy 1.19.1 rejects it.",
    },
    {
        "id": "GA06",
        "file": "GA06-ordinary-generic-excess.py",
        "subject": "ordinary Generic[T] excess arguments",
        "provenance": "negative control",
        "runtime_exit": 1,
        "mypy_1_19_1_exit": 1,
        "expected": "Both CPython and mypy reject two arguments for one TypeVar.",
    },
    {
        "id": "DC01",
        "file": "DC01-original-posted-dataclass.py",
        "subject": "verbatim posted dataclass",
        "provenance": "verbatim code block from frozen dataclass TIL body",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "Runtime prints C/C2; bare generic construction may require an annotation.",
    },
    {
        "id": "DC02",
        "file": "DC02-unsuppressed-default.py",
        "subject": "unsuppressed bound-TypeVar factory mismatch",
        "provenance": "independent minimal counterexample",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "Checker reports assignment mismatch; runtime constructs C for MyClass[C2].",
    },
    {
        "id": "DC03",
        "file": "DC03-targeted-ignore.py",
        "subject": "targeted ignore with direct specialization",
        "provenance": "independent minimal counterexample",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 0,
        "expected": "Checker reveals C2 after suppression while runtime still constructs C.",
    },
    {
        "id": "DC04",
        "file": "DC04-required-field.py",
        "subject": "required-field correction",
        "provenance": "independent sound alternative",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 0,
        "expected": "Checker and runtime agree on C2.",
    },
    {
        "id": "DC05",
        "file": "DC05-caller-factory.py",
        "subject": "caller-supplied typed factory",
        "provenance": "independent sound alternative",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 0,
        "expected": "Checker and runtime agree on C2.",
    },
    {
        "id": "DC06",
        "file": "DC06-concrete-subclass-factory.py",
        "subject": "concrete subclass factory override",
        "provenance": "independent sound alternative",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 0,
        "expected": "Concrete annotation and factory both produce C2.",
    },
    {
        "id": "DC07",
        "file": "DC07-bare-versus-annotated.py",
        "subject": "bare versus annotated generic instances",
        "provenance": "independent inference fixture",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "Bare construction is rejected; explicit annotations reveal C and C2, but runtime factory always returns C.",
    },
    {
        "id": "NC01",
        "file": "NC01-incorrect-type-assertion.py",
        "subject": "incorrect exact type assertion",
        "provenance": "negative control",
        "runtime_exit": 0,
        "mypy_1_19_1_exit": 1,
        "expected": "Checker rejects an intentionally wrong exact-type assertion.",
    },
]

DIAGNOSTIC = re.compile(
    r"^(?P<path>FIXTURES/[^:]+):(?P<line>\d+)(?::(?P<column>\d+))?: "
    r"(?P<severity>error|note): (?P<message>.*?)(?:  \[(?P<code>[^]]+)\])?$"
)


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPOSITORY.resolve()).as_posix()
    except ValueError:
        pass
    try:
        return "$HOME/" + resolved.relative_to(HOME.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def normalize_text(value: str) -> str:
    return value.replace(str(REPOSITORY), "<REPOSITORY>").replace(str(HOME), "$HOME")


def source_inventory() -> list[dict[str, Any]]:
    paths = sorted(
        [*FIXTURES.glob("*.py"), *Path(__file__).resolve().parent.glob("*.py")],
        key=lambda item: item.relative_to(ROOT).as_posix(),
    )
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def bounded_pyright_search() -> dict[str, Any]:
    """Search already-present tool/cache roots without invoking npm or uv."""
    name_roots = [
        HOME / ".cache/uv",
        HOME / ".local/opt/node",
        Path("/usr/local/lib"),
        Path("/usr/lib"),
    ]
    matches: set[str] = set()
    for root in name_roots:
        if not root.exists():
            continue
        root_depth = len(root.parts)
        for current, directories, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            if len(current_path.parts) - root_depth >= 7:
                directories[:] = []
            for name in [*directories, *files]:
                normalized_name = name.casefold()
                if re.search(r"(?:^|[-_.])(?:based)?pyright(?:$|[-_.])", normalized_name):
                    matches.add(display_path(current_path / name))

    npm_index = HOME / ".npm/_cacache/index-v5"
    npm_index_hits: list[str] = []
    if npm_index.is_dir():
        for path in npm_index.rglob("*"):
            if not path.is_file() or path.stat().st_size > 1_000_000:
                continue
            if b"pyright" in path.read_bytes().lower():
                npm_index_hits.append(display_path(path))

    return {
        "name_search_roots": [display_path(path) for path in name_roots],
        "name_matches": sorted(matches),
        "npm_index_root": display_path(npm_index),
        "npm_index_content_matches": sorted(npm_index_hits),
        "max_name_search_depth": 7,
        "max_npm_index_file_bytes": 1_000_000,
    }


def run_command(argv: list[str], *, label: str, timeout: int = 60) -> dict[str, Any]:
    env = os.environ.copy()
    env.update({
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "UV_NO_PROGRESS": "1",
    })
    started = utc_now()
    result = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    finished = utc_now()
    stdout = normalize_text(result.stdout.decode("utf-8", errors="replace"))
    stderr = normalize_text(result.stderr.decode("utf-8", errors="replace"))
    normalized_argv = [normalize_text(value) for value in argv]
    return {
        "label": label,
        "argv": normalized_argv,
        "cwd": "evidence/LOCAL-VERIFY-002",
        "environment_overrides": {
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "UV_NO_PROGRESS": "1",
        },
        "started_at_utc": started,
        "finished_at_utc": finished,
        "exit_code": result.returncode,
        "stdout": stdout,
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stdout_sha256": sha256_bytes(stdout.encode("utf-8")),
        "stderr": stderr,
        "stderr_bytes": len(stderr.encode("utf-8")),
        "stderr_sha256": sha256_bytes(stderr.encode("utf-8")),
    }


def write_json(path: Path, value: object) -> dict[str, Any]:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def parse_diagnostics(stdout: str, stderr: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for stream, text in (("stdout", stdout), ("stderr", stderr)):
        for line in text.splitlines():
            match = DIAGNOSTIC.match(line)
            if not match:
                continue
            row = match.groupdict()
            parsed.append({
                "stream": stream,
                "path": row["path"],
                "line": int(row["line"]),
                "column": int(row["column"]) if row["column"] else None,
                "severity": row["severity"],
                "message": row["message"],
                "code": row["code"],
            })
    return parsed


def stable_projection(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in ("argv", "cwd", "environment_overrides", "exit_code", "stdout", "stderr")
    }


def check(condition: bool, check_id: str, checks: list[dict[str, Any]], **details: Any) -> None:
    row = {"id": check_id, "passed": bool(condition), **details}
    checks.append(row)
    if not condition:
        raise AssertionError(f"{check_id}: {details}")


def find_result(results: list[dict[str, Any]], fixture_id: str) -> dict[str, Any]:
    return next(item for item in results if item["fixture_id"] == fixture_id)


def main() -> int:
    RAW.mkdir(exist_ok=True)
    started = utc_now()
    before = source_inventory()
    checks: list[dict[str, Any]] = []
    raw_files: list[dict[str, Any]] = []

    # Tool discovery is deliberately separate from evidence execution. The uvx
    # probe is offline; no npm command or Pyright wrapper is invoked.
    mypy_path = Path(shutil.which("mypy") or "")
    node_path = Path(shutil.which("node") or "")
    uv_path = Path(shutil.which("uv") or "")
    pyright_path = shutil.which("pyright")
    basedpyright_path = shutil.which("basedpyright")
    tool_commands = {
        "mypy_version": run_command([str(mypy_path), "--version"], label="tool-mypy-1.19.1-version"),
        "mypy_1_19_1_offline_probe": run_command(
            ["uvx", "--offline", "--from", "mypy==1.19.1", "mypy", "--version"],
            label="tool-mypy-1.19.1-offline-cache-probe",
        ),
        "mypy_2_3_1_offline_probe": run_command(
            ["uvx", "--offline", "--from", "mypy==2.3.1", "mypy", "--version"],
            label="tool-mypy-2.3.1-offline-cache-probe",
        ),
        "node_version": run_command([str(node_path), "--version"], label="tool-node-version"),
        "uv_version": run_command(["uv", "--version"], label="tool-uv-version"),
        "mypy_debian_package": run_command(
            ["dpkg-query", "-W", "-f=${Package}\\t${Version}\\t${Architecture}\\n", "mypy"],
            label="tool-mypy-debian-package",
        ),
    }
    for version, executable in PYTHONS.items():
        tool_commands[f"python_{version}_version"] = run_command(
            [str(executable), "--version"],
            label=f"tool-python-{version}-version",
        )
    pyright_cache_search = bounded_pyright_search()
    tool_inventory = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "checked_at_utc": utc_now(),
        "commands": tool_commands,
        "executables": {
            "mypy": {
                "path": display_path(mypy_path),
                "bytes": mypy_path.stat().st_size,
                "sha256": sha256_file(mypy_path),
            },
            "node": {
                "path": display_path(node_path),
                "resolved_path": display_path(node_path.resolve()),
                "bytes": node_path.resolve().stat().st_size,
                "sha256": sha256_file(node_path.resolve()),
            },
            "uv": {
                "path": display_path(uv_path),
                "resolved_path": display_path(uv_path.resolve()),
                "bytes": uv_path.resolve().stat().st_size,
                "sha256": sha256_file(uv_path.resolve()),
            },
            "python": {
                version: {
                    "path": display_path(path),
                    "resolved_path": display_path(path.resolve()),
                    "bytes": path.resolve().stat().st_size,
                    "sha256": sha256_file(path.resolve()),
                }
                for version, path in PYTHONS.items()
            },
            "pyright": pyright_path,
            "basedpyright": basedpyright_path,
        },
        "pyright_bounded_cache_search": pyright_cache_search,
        "coverage": {
            "mypy_1.19.1": "EXECUTED_NATIVE",
            "mypy_2.3.1": "NOT_TESTED",
            "pyright_1.1.414": "NOT_TESTED",
        },
        "bootstrap_boundary": {
            "npm_invoked": False,
            "npx_invoked": False,
            "pyright_wrapper_invoked": False,
            "downloads_permitted": False,
        },
    }
    raw_files.append(write_json(RAW / "tool-inventory.json", tool_inventory))
    check(tool_commands["mypy_version"]["exit_code"] == 0, "TOOL-mypy-version-exit", checks)
    check("mypy 1.19.1" in tool_commands["mypy_version"]["stdout"], "TOOL-mypy-version-exact", checks)
    check(
        tool_commands["mypy_1_19_1_offline_probe"]["exit_code"] != 0
        and "mypy was not found in the cache" in tool_commands["mypy_1_19_1_offline_probe"]["stderr"],
        "TOOL-mypy-1.19.1-uvx-cache-miss-system-package-retained",
        checks,
    )
    check(tool_commands["mypy_2_3_1_offline_probe"]["exit_code"] != 0, "TOOL-mypy-2.3.1-cache-miss", checks)
    check(
        "mypy was not found in the cache" in tool_commands["mypy_2_3_1_offline_probe"]["stderr"],
        "TOOL-mypy-2.3.1-no-download",
        checks,
    )
    check(pyright_path is None and basedpyright_path is None, "TOOL-pyright-unavailable", checks)
    check(
        not pyright_cache_search["name_matches"]
        and not pyright_cache_search["npm_index_content_matches"],
        "TOOL-pyright-bounded-cache-search-empty",
        checks,
    )

    fixture_by_id = {item["id"]: item for item in FIXTURE_SPECS}
    fixture_inventory = []
    for spec in FIXTURE_SPECS:
        path = FIXTURES / spec["file"]
        fixture_inventory.append({
            **spec,
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    raw_files.append(write_json(RAW / "fixture-inventory.json", fixture_inventory))

    # Static checker matrix: every applicable fixture, default and strict, in
    # two independent processes. No incremental cache is used.
    mypy_runs: dict[tuple[str, int], list[dict[str, Any]]] = {}
    common_mypy = [
        str(mypy_path),
        "--no-incremental",
        "--show-error-codes",
        "--show-column-numbers",
        "--no-pretty",
        "--no-color-output",
        "--no-error-summary",
    ]
    for mode in ("default", "strict"):
        for repeat in (1, 2):
            results: list[dict[str, Any]] = []
            for spec in FIXTURE_SPECS:
                args = [*common_mypy]
                if mode == "strict":
                    args.append("--strict")
                args.append(f"FIXTURES/{spec['file']}")
                command = run_command(
                    args,
                    label=f"mypy-1.19.1-{mode}-{spec['id']}-fresh-{repeat}",
                )
                command.update({
                    "fixture_id": spec["id"],
                    "fixture_sha256": next(
                        item["sha256"] for item in fixture_inventory if item["id"] == spec["id"]
                    ),
                    "mode": mode,
                    "repeat": repeat,
                    "diagnostics": parse_diagnostics(command["stdout"], command["stderr"]),
                    "expected_exit_code": spec["mypy_1_19_1_exit"],
                    "expected_behavior": spec["expected"],
                })
                results.append(command)
            mypy_runs[(mode, repeat)] = results
            raw_files.append(write_json(RAW / f"mypy-1.19.1-{mode}-run-{repeat}.json", results))

    for mode in ("default", "strict"):
        first = mypy_runs[(mode, 1)]
        second = mypy_runs[(mode, 2)]
        for left, right in zip(first, second, strict=True):
            spec = fixture_by_id[left["fixture_id"]]
            check(
                left["exit_code"] == spec["mypy_1_19_1_exit"],
                f"MYPY-{mode}-{left['fixture_id']}-expected-exit",
                checks,
                expected=spec["mypy_1_19_1_exit"],
                actual=left["exit_code"],
            )
            check(
                stable_projection(left) == stable_projection(right),
                f"MYPY-{mode}-{left['fixture_id']}-fresh-process-determinism",
                checks,
            )

    default_results = mypy_runs[("default", 1)]

    def codes(fixture_id: str) -> set[str | None]:
        return {item["code"] for item in find_result(default_results, fixture_id)["diagnostics"]}

    # Negative controls demonstrate the harness catches each relevant class.
    negative_controls = [
        {
            "id": "NC-static-excess-arguments",
            "passed": "type-arg" in codes("GA06"),
            "fixture": "GA06",
            "expected": "mypy diagnostic code type-arg",
            "actual_codes": sorted(code for code in codes("GA06") if code),
        },
        {
            "id": "NC-static-literal-ellipsis",
            "passed": "misc" in codes("GA05"),
            "fixture": "GA05",
            "expected": "mypy diagnostic code misc",
            "actual_codes": sorted(code for code in codes("GA05") if code),
        },
        {
            "id": "NC-static-unsound-factory",
            "passed": "assignment" in codes("DC02"),
            "fixture": "DC02",
            "expected": "mypy diagnostic code assignment",
            "actual_codes": sorted(code for code in codes("DC02") if code),
        },
        {
            "id": "NC-static-wrong-assertion",
            "passed": "assert-type" in codes("NC01"),
            "fixture": "NC01",
            "expected": "mypy diagnostic code assert-type",
            "actual_codes": sorted(code for code in codes("NC01") if code),
        },
        {
            "id": "NC-harness-changed-exit",
            "passed": find_result(default_results, "GA06")["exit_code"] != 0,
            "fixture": "GA06",
            "expected": "deliberately wrong expected exit 0 is detected",
            "actual_exit": find_result(default_results, "GA06")["exit_code"],
        },
        {
            "id": "NC-harness-changed-diagnostic",
            "passed": "assert-typo" not in codes("NC01") and "assert-type" in codes("NC01"),
            "fixture": "NC01",
            "expected": "changed diagnostic code assert-typo does not match",
            "actual_codes": sorted(code for code in codes("NC01") if code),
        },
    ]
    for item in negative_controls:
        check(item["passed"], item["id"], checks, fixture=item["fixture"])

    # Runtime matrix across every installed CPython, repeated in fresh processes.
    runtime_runs: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for version, executable in PYTHONS.items():
        version_probe = tool_commands[f"python_{version}_version"]
        check(version_probe["exit_code"] == 0, f"PYTHON-{version}-version-exit", checks)
        check(version in version_probe["stdout"], f"PYTHON-{version}-version-exact", checks)
        for repeat in (1, 2):
            results = []
            for spec in FIXTURE_SPECS:
                command = run_command(
                    [str(executable), f"FIXTURES/{spec['file']}"],
                    label=f"runtime-{version}-{spec['id']}-fresh-{repeat}",
                )
                command.update({
                    "fixture_id": spec["id"],
                    "fixture_sha256": next(
                        item["sha256"] for item in fixture_inventory if item["id"] == spec["id"]
                    ),
                    "python_version": version,
                    "repeat": repeat,
                    "expected_exit_code": spec["runtime_exit"],
                    "expected_behavior": spec["expected"],
                })
                results.append(command)
            runtime_runs[(version, repeat)] = results
            raw_files.append(write_json(RAW / f"runtime-{version}-run-{repeat}.json", results))

    for version in PYTHONS:
        first = runtime_runs[(version, 1)]
        second = runtime_runs[(version, 2)]
        for left, right in zip(first, second, strict=True):
            spec = fixture_by_id[left["fixture_id"]]
            check(
                left["exit_code"] == spec["runtime_exit"],
                f"RUNTIME-{version}-{left['fixture_id']}-expected-exit",
                checks,
                expected=spec["runtime_exit"],
                actual=left["exit_code"],
            )
            check(
                stable_projection(left) == stable_projection(right),
                f"RUNTIME-{version}-{left['fixture_id']}-fresh-process-determinism",
                checks,
            )

    runtime_314 = runtime_runs[("3.14.4", 1)]
    dc03_runtime = json.loads(find_result(runtime_314, "DC03")["stdout"])
    ga02_runtime = json.loads(find_result(runtime_314, "GA02")["stdout"])
    ga05_runtime = json.loads(find_result(runtime_314, "GA05")["stdout"])
    runtime_negative_controls = [
        {
            "id": "NC-runtime-verbatim-genericalias",
            "passed": "GenericAlias' is not subscriptable" in find_result(runtime_314, "GA01")["stderr"],
            "fixture": "GA01",
            "expected": "TypeError before class declaration",
        },
        {
            "id": "NC-runtime-ordinary-generic-arity",
            "passed": "Too many arguments" in find_result(runtime_314, "GA06")["stderr"],
            "fixture": "GA06",
            "expected": "TypeError for excess ordinary generic arguments",
        },
        {
            "id": "NC-runtime-genericalias-non-enforcement",
            "passed": ga02_runtime["unchecked_value"] == [1, "unchecked"],
            "fixture": "GA02",
            "expected": "metadata does not enforce tuple elements",
        },
        {
            "id": "NC-runtime-suppressed-factory-defect",
            "passed": dc03_runtime == {
                "declared": "MyClass[C2]",
                "runtime_var_type": "C",
                "satisfies_C2": False,
            },
            "fixture": "DC03",
            "expected": "suppression leaves C where C2 is declared",
        },
        {
            "id": "NC-runtime-ellipsis-metadata",
            "passed": ga05_runtime["ellipsis_args"] == ["<class 'int'>", "Ellipsis"],
            "fixture": "GA05",
            "expected": "CPython accepts literal ellipsis metadata",
        },
    ]
    negative_controls.extend(runtime_negative_controls)
    for item in runtime_negative_controls:
        check(item["passed"], item["id"], checks, fixture=item["fixture"])

    raw_files.append(write_json(ROOT / "NEGATIVE-CONTROLS.json", {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "control_count": len(negative_controls),
        "failed_control_count": sum(not item["passed"] for item in negative_controls),
        "controls": negative_controls,
    }))

    after = source_inventory()
    check(before == after, "SOURCE-inventory-unchanged-during-execution", checks)

    determinism = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "source_inventory_before": before,
        "source_inventory_after": after,
        "source_unchanged": before == after,
        "mypy_fresh_process_pairs": 2 * len(FIXTURE_SPECS),
        "runtime_fresh_process_pairs": len(PYTHONS) * len(FIXTURE_SPECS),
        "all_pairs_identical": all(
            item["passed"] for item in checks if item["id"].endswith("fresh-process-determinism")
        ),
    }
    raw_files.append(write_json(RAW / "determinism.json", determinism))

    execution = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "seed": SEED,
        "network_access": False,
        "downloads": False,
        "npm_invoked": False,
        "source_inventory_unchanged": before == after,
        "source_inventory": before,
        "fixture_count": len(FIXTURE_SPECS),
        "mypy_executed_result_rows": 2 * len(FIXTURE_SPECS),
        "mypy_fresh_process_command_count": 4 * len(FIXTURE_SPECS),
        "runtime_result_rows": len(PYTHONS) * len(FIXTURE_SPECS),
        "runtime_fresh_process_command_count": 2 * len(PYTHONS) * len(FIXTURE_SPECS),
        "negative_control_count": len(negative_controls),
        "failed_negative_control_count": sum(not item["passed"] for item in negative_controls),
        "check_count": len(checks),
        "failed_check_count": sum(not item["passed"] for item in checks),
        "checks": checks,
        "raw_files": raw_files,
        "orchestrator": {
            "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "bytes": Path(__file__).stat().st_size,
            "sha256": sha256_file(Path(__file__).resolve()),
            "python": platform.python_version(),
            "invocation": [
                "uv", "run", "--no-project", "--offline", "--no-managed-python",
                "python", "RUNNER/run_matrix.py",
            ],
        },
    }
    write_json(RAW / "EXECUTION.json", execution)
    print(json.dumps({
        "campaign": "LOCAL-VERIFY-002",
        "failed_checks": execution["failed_check_count"],
        "fixtures": execution["fixture_count"],
        "mypy_rows": execution["mypy_executed_result_rows"],
        "negative_controls": execution["negative_control_count"],
        "runtime_rows": execution["runtime_result_rows"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
