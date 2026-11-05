#!/usr/bin/env python3
"""Collect a privacy-bounded LOCAL-VERIFY-003 native environment receipt."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "RAW"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv: list[str]) -> dict[str, Any]:
    completed = subprocess.run(argv, capture_output=True, check=False, text=True)
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip('"')
    return result


def cpu_model() -> str:
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def package_tree() -> dict[str, Any]:
    root = Path("/usr/lib/python3/dist-packages/yt_dlp")
    records: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        records.append((path.relative_to(root).as_posix(), sha256(path)))
    digest = hashlib.sha256()
    for relative, value in records:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return {
        "root": "/usr/lib/python3/dist-packages/yt_dlp",
        "file_count": len(records),
        "aggregate_sha256": digest.hexdigest(),
    }


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is unavailable")
    commands = {
        "yt_dlp_version": command(["/usr/bin/yt-dlp", "--version"]),
        "python_version": command(["/usr/bin/python3", "--version"]),
        "uv_version": command(["uv", "--version"]),
        "package_status": command(
            [
                "dpkg-query",
                "-W",
                "-f=${Package}\\t${Version}\\t${Architecture}\\t${Status}\\n",
                "yt-dlp",
            ]
        ),
        "module_identity": command(
            [
                "uv",
                "run",
                "--no-project",
                "--offline",
                "--no-managed-python",
                "python",
                "-c",
                (
                    "import json,sys,yt_dlp; from importlib import metadata; "
                    "from yt_dlp.version import __version__; "
                    "print(json.dumps({'python':sys.version,'executable':sys.executable,"
                    "'yt_dlp_version':__version__,'distribution_version':metadata.version('yt-dlp'),"
                    "'module':yt_dlp.__file__},sort_keys=True))"
                ),
            ]
        ),
    }
    critical = [
        Path("/usr/bin/yt-dlp"),
        Path("/usr/lib/python3/dist-packages/yt_dlp/version.py"),
        Path("/usr/lib/python3/dist-packages/yt_dlp/YoutubeDL.py"),
        Path("/usr/lib/python3/dist-packages/yt_dlp/__init__.py"),
    ]
    environment = {
        "campaign": "LOCAL-VERIFY-003",
        "recorded_at_utc": now(),
        "operating_system": {
            "os_release": os_release(),
            "kernel_release": platform.release(),
            "architecture": platform.machine(),
        },
        "cpu": {
            "model": cpu_model(),
            "logical_cpu_count": os.cpu_count(),
        },
        "python": {
            "executable": "/usr/bin/python3",
            "version_output": commands["python_version"]["stdout"].strip(),
            "module_probe": json.loads(commands["module_identity"]["stdout"]),
        },
        "uv": {
            "executable": "$HOME/.local/bin/uv",
            "bytes": Path(uv).stat().st_size,
            "sha256": sha256(Path(uv)),
            "version_output": commands["uv_version"]["stdout"].strip(),
        },
        "yt_dlp": {
            "executable": "/usr/bin/yt-dlp",
            "version_output": commands["yt_dlp_version"]["stdout"].strip(),
            "distribution": commands["package_status"]["stdout"].strip(),
            "critical_file_identities": [
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in critical
            ],
            "package_tree": package_tree(),
        },
        "safety": {
            "live_extractor_invoked": False,
            "subtitle_download_invoked": False,
            "network_access_authorized": False,
            "network_access_observed": False,
            "credentials_used": False,
            "dependencies_installed_or_upgraded": False,
        },
    }
    if any(item["exit_code"] != 0 for item in commands.values()):
        raise SystemExit("environment command failed")
    (RAW / "ENVIRONMENT-COMMANDS.json").write_text(
        json.dumps(
            {"campaign": "LOCAL-VERIFY-003", "commands": commands},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (ROOT / "ENVIRONMENT.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
