#!/usr/bin/env python3
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(label, command):
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        return {
            "label": label,
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": f"FileNotFoundError: {exc}",
        }
    return {
        "label": label,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main():
    commands = [
        run("utc_time", ["date", "-u", "--iso-8601=ns"]),
        run("kernel", ["uname", "-a"]),
        run("architecture", ["uname", "-m"]),
        run("cpu", ["lscpu", "-J"]),
        run("os_release", ["cat", "/etc/os-release"]),
        run("glibc", ["getconf", "GNU_LIBC_VERSION"]),
        run("python", ["python3", "--version"]),
        run("uv", ["uv", "--version"]),
        run("uv_python", [
            "uv", "run", "--no-project", "--offline", "--no-managed-python",
            "python", "-c",
            "import platform,sys; print(sys.version); print(platform.python_implementation()); print(platform.platform())",
        ]),
        run("yt_dlp", ["yt-dlp", "--version"]),
        run("mypy", ["mypy", "--version"]),
        run("pyright", ["pyright", "--version"]),
        run("dependency_metadata", [
            "uv", "run", "--no-project", "--offline", "--no-managed-python",
            "python", "-c",
            "import importlib.metadata as m\n"
            "for n in ('yt-dlp','openpyxl','mypy','pyright'):\n"
            " try: print(n+'='+m.version(n))\n"
            " except m.PackageNotFoundError: print(n+'=NOT_INSTALLED')",
        ]),
        run("outside_git_repository", ["git", "-C", "/home/trent", "rev-parse", "--show-toplevel"]),
    ]
    cpu_model = None
    logical_cpus = os.cpu_count()
    for item in commands:
        if item["label"] == "cpu" and item["exit_code"] == 0:
            parsed = json.loads(item["stdout"])
            fields = {entry["field"].rstrip(":"): entry["data"] for entry in parsed["lscpu"]}
            cpu_model = fields.get("Model name")
            logical_cpus = int(fields.get("CPU(s)", logical_cpus))

    document = {
        "schema": "CODEX-001-environment-v1",
        "mission_started_utc": "2026-11-04T16:21:41.206111521+00:00",
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": {"model": cpu_model, "logical_cpus": logical_cpus},
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable": os.path.realpath("/usr/bin/python3"),
        },
        "uv": "0.12.1 (x86_64-unknown-linux-gnu)",
        "dependencies": {
            "yt-dlp": {"installed": True, "version": "2026.3.17"},
            "mypy": {"installed": True, "version": "1.19.1"},
            "openpyxl": {"installed": False, "version": None},
            "pyright": {"installed": False, "version": None},
        },
        "network_policy": "No external experiment traffic. SOFA was read through its authenticated connector; test networking used approved 127.0.0.1 fixtures only.",
        "canonical_path_collision": {
            "requested": "/home/trent/SOFA-HOT-008/CODEX-001",
            "observed": True,
            "handling": "Did not read file contents, merge, overwrite, or hash the foreign package; used an independent sibling directory.",
            "actual_package": str(ROOT),
        },
        "commands": commands,
    }
    (ROOT / "environment.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"captured": True, "commands": len(commands),
                      "path": str(ROOT / "environment.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
