#!/usr/bin/env python3
"""Record executable and bounded local-cache availability for static checkers."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CROSS-CHECKS" / "checker-inventory.json"
SEARCH_ROOTS = [Path("/home/trent/.cache"), Path("/home/trent/.local")]
TARGET_NAMES = {"pyright", "basedpyright"}
TARGET_FRAGMENTS = {"pyright-1.1.414", "mypy-2.3.1"}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    matches: list[str] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            name = path.name.lower()
            if name in TARGET_NAMES or any(fragment in name for fragment in TARGET_FRAGMENTS):
                matches.append(str(path))
    uv_tools = subprocess.run(
        ["uv", "tool", "list"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    source = Path(__file__).resolve()
    result = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "recorded_at_utc": utc_now(),
        "source": {
            "path": source.relative_to(ROOT).as_posix(),
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
        },
        "executables": {
            name: shutil.which(name)
            for name in ("mypy", "pyright", "basedpyright")
        },
        "uv_tool_list": {
            "argv": ["uv", "tool", "list"],
            "exit_code": uv_tools.returncode,
            "stdout": uv_tools.stdout,
            "stderr": uv_tools.stderr,
        },
        "bounded_cache_search": {
            "roots": [str(path) for path in SEARCH_ROOTS],
            "name_targets": sorted(TARGET_NAMES),
            "version_fragments": sorted(TARGET_FRAGMENTS),
            "matches": sorted(matches),
        },
        "coverage": {
            "mypy_1.19.1": "EXECUTED_NATIVE",
            "mypy_2.3.1": "NOT_TESTED",
            "pyright_1.1.414": "NOT_TESTED",
            "basedpyright": "NOT_TESTED",
        },
        "installation_performed": False,
        "node_or_npm_invoked": False,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "sha256": sha256(OUTPUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
