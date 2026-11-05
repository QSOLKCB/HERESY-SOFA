#!/usr/bin/env python3
"""Prepare LOCAL-VERIFY-002B checkers from archived distributions, offline."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "PACKAGES"
METADATA = PACKAGES / "METADATA"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def execute(argv: list[str], *, env: dict[str, str]) -> dict[str, Any]:
    started = utc_now()
    result = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    receipt = {
        "argv": argv,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode:
        raise RuntimeError(json.dumps(receipt, indent=2))
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--uv", required=True, type=Path)
    parser.add_argument("--python", default=Path("/usr/bin/python3.14"), type=Path)
    parser.add_argument("--node", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.resolve()
    if target.exists():
        raise SystemExit(f"refusing existing preparation target: {target}")
    target.mkdir(parents=True)
    environment = os.environ.copy()
    environment.update({"UV_OFFLINE": "1", "UV_NO_PROGRESS": "1", "LC_ALL": "C.UTF-8"})
    receipts: list[dict[str, Any]] = []

    pyright_root = target / "pyright"
    inspection_receipt = target / "package-inspection.json"
    inspection = [
        sys.executable,
        str(ROOT / "RUNNER/inspect_packages.py"),
        "--mypy-wheel", str(PACKAGES / "mypy-2.3.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"),
        "--mypy-pypi-json", str(METADATA / "mypy-2.3.1-pypi.json"),
        "--librt-wheel", str(PACKAGES / "librt-0.16.0-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"),
        "--librt-pypi-json", str(METADATA / "librt-pypi.json"),
        "--ast-serialize-wheel", str(PACKAGES / "ast_serialize-0.13.1-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"),
        "--ast-serialize-pypi-json", str(METADATA / "ast-serialize-pypi.json"),
        "--typing-extensions-wheel", str(PACKAGES / "typing_extensions-4.15.0-py3-none-any.whl"),
        "--typing-extensions-pypi-json", str(METADATA / "typing-extensions-4.15.0-pypi.json"),
        "--mypy-extensions-wheel", str(PACKAGES / "mypy_extensions-1.1.0-py3-none-any.whl"),
        "--mypy-extensions-pypi-json", str(METADATA / "mypy-extensions-1.1.0-pypi.json"),
        "--pathspec-wheel", str(PACKAGES / "pathspec-1.0.4-py3-none-any.whl"),
        "--pathspec-pypi-json", str(METADATA / "pathspec-1.0.4-pypi.json"),
        "--pyright-tgz", str(PACKAGES / "pyright-1.1.414.tgz"),
        "--pyright-registry-json", str(METADATA / "pyright-1.1.414-registry.json"),
        "--extract-pyright", str(pyright_root),
        "--output", str(inspection_receipt),
    ]
    receipts.append(execute(inspection, env=environment))

    venv = target / "mypy-venv"
    receipts.append(execute([
        str(args.uv), "venv", "--offline", "--python", str(args.python), str(venv)
    ], env=environment))
    wheels = [
        PACKAGES / "mypy-2.3.1-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl",
        PACKAGES / "librt-0.16.0-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl",
        PACKAGES / "ast_serialize-0.13.1-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        PACKAGES / "typing_extensions-4.15.0-py3-none-any.whl",
        PACKAGES / "mypy_extensions-1.1.0-py3-none-any.whl",
        PACKAGES / "pathspec-1.0.4-py3-none-any.whl",
    ]
    receipts.append(execute([
        str(args.uv), "pip", "install", "--offline", "--no-deps",
        "--python", str(venv / "bin/python"), *map(str, wheels)
    ], env=environment))
    receipts.append(execute([
        str(args.uv), "pip", "check", "--python", str(venv / "bin/python")
    ], env=environment))
    receipts.append(execute([str(venv / "bin/mypy"), "--version"], env=environment))
    receipts.append(execute([
        str(args.node), str(pyright_root / "package/index.js"), "--version"
    ], env=environment))

    final = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "prepared_at_utc": utc_now(),
        "offline": True,
        "target": str(target),
        "mypy_executable": str(venv / "bin/mypy"),
        "python_executable": str(venv / "bin/python"),
        "pyright_entrypoint": str(pyright_root / "package/index.js"),
        "node_executable": str(args.node),
        "receipts": receipts,
    }
    (target / "setup-receipt.json").write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "mypy": receipts[-2]["stdout"].strip(),
        "pyright": receipts[-1]["stdout"].strip(),
        "target": str(target),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
