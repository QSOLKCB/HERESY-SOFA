#!/usr/bin/env python3
"""Collect the immutable pre-experiment environment inventory for LOCAL-VERIFY-001."""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.metadata
import json
import locale
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "REPORTS" / "LOCAL-VERIFY-001-ENVIRONMENT.json"
REPOSITORY = Path("/home/trent/HERESY-SOFA")
PR16 = "22083e28949d5691731f8cf16ed80fae23899980"
PR17 = "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    started = utc_now()
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        return {
            "argv": argv,
            "cwd": str(cwd) if cwd else str(ROOT),
            "started_at_utc": started,
            "finished_at_utc": utc_now(),
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "argv": argv,
            "cwd": str(cwd) if cwd else str(ROOT),
            "started_at_utc": started,
            "finished_at_utc": utc_now(),
            "exit_code": None,
            "exception": f"{type(exc).__name__}: {exc}",
        }


def distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def cpu_model() -> str | None:
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def resolve_tool(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"available": path is not None, "path": path}


def git_text(argv: list[str]) -> str:
    result = subprocess.run(
        ["git", *argv], cwd=REPOSITORY, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return result.stdout.strip()


def is_ancestor(commit: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, descendant],
        cwd=REPOSITORY, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.returncode == 0


def main() -> int:
    source = Path(__file__).resolve()
    inventory: dict[str, Any] = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "recorded_before_experiments": True,
        "recorded_at_utc": utc_now(),
        "privacy": {
            "hostname_recorded": False,
            "credentials_accessed": False,
            "external_services_contacted": False,
        },
        "collector": {
            "path": str(source.relative_to(ROOT)),
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
            "invocation": [
                "uv", "run", "--no-project", "--offline",
                "--no-managed-python", "python", str(source),
            ],
        },
        "operating_system": {
            "os_release": os_release(),
            "kernel_release": platform.release(),
            "kernel_version": platform.version(),
            "architecture": platform.machine(),
            "byte_order": sys.byteorder,
            "cpu_model": cpu_model(),
            "logical_cpu_count": os.cpu_count(),
            "lscpu": command(["lscpu", "--json"]),
        },
        "python": {
            "version": platform.python_version(),
            "version_verbose": sys.version,
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "build": list(platform.python_build()),
            "executable": sys.executable,
            "cache_tag": sys.implementation.cache_tag,
        },
        "locale_and_time": {
            "timezone_file": Path("/etc/timezone").read_text(encoding="utf-8").strip()
                if Path("/etc/timezone").exists() else None,
            "tz_environment": os.environ.get("TZ"),
            "preferred_encoding": locale.getpreferredencoding(False),
            "locale_command": command(["locale"]),
        },
        "tools": {
            name: resolve_tool(name)
            for name in ("uv", "mypy", "yt-dlp", "pyright", "basedpyright", "node", "npm")
        },
        "distributions": {
            name: distribution_version(name)
            for name in (
                "mypy", "yt-dlp", "openpyxl", "pyright",
                "basedpyright", "typing_extensions",
            )
        },
        "version_commands": {
            "uv": command(["uv", "--version"]),
            "uv_tools": command(["uv", "tool", "list"]),
            "mypy": command(["mypy", "--version"]),
            "yt_dlp": command(["yt-dlp", "--version"]),
            "pyright": command(["pyright", "--version"]),
            "basedpyright": command(["basedpyright", "--version"]),
        },
        "repository": {
            "path": str(REPOSITORY),
            "working_head": git_text(["rev-parse", "HEAD"]),
            "working_branch": git_text(["branch", "--show-current"]),
            "working_tree_status": git_text(["status", "--porcelain=v1"]),
            "origin_main": git_text(["rev-parse", "origin/main"]),
            "pr16_merge_commit": PR16,
            "pr17_merge_commit": PR17,
            "pr16_is_ancestor_of_origin_main": is_ancestor(PR16, "origin/main"),
            "pr17_is_ancestor_of_origin_main": is_ancestor(PR17, "origin/main"),
        },
        "checker_coverage": {
            "mypy_1_19_1": "AVAILABLE",
            "mypy_2_3_1": "NOT_FOUND_IN_PATH_UV_TOOLS_OR_UV_CACHE",
            "pyright_1_1_414": "NOT_FOUND_IN_PATH_UV_TOOLS_OR_UV_CACHE",
            "basedpyright": "NOT_FOUND_IN_PATH_UV_TOOLS_OR_UV_CACHE",
        },
        "constraints": {
            "dependency_installation": "forbidden_and_not_performed",
            "network_tests": "forbidden_and_not_performed",
            "seed": 26051105,
        },
    }
    OUTPUT.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(OUTPUT),
        "sha256": sha256(OUTPUT),
        "recorded_at_utc": inventory["recorded_at_utc"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
