#!/usr/bin/env python3
"""Finalize LOCAL-VERIFY-002 archive metadata and SHA-256 ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "ARCHIVE.json"
LEDGER = ROOT / "SHA256SUMS.txt"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def regular_files(*, include_archive: bool) -> list[Path]:
    excluded = {LEDGER}
    if not include_archive:
        excluded.add(ARCHIVE)
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path in excluded:
            continue
        if path.is_symlink():
            raise SystemExit(f"symlink not allowed: {path.relative_to(ROOT)}")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise SystemExit(f"unexpected file type: {path.relative_to(ROOT)}")
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256(data),
        "git_blob_sha": git_blob(data),
    }


def main() -> int:
    payload = [record(path) for path in regular_files(include_archive=False)]
    archive = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "archive_state": "native_static_checker_matrix_finalized",
        "repository_source_commit": "ddccc1214b7a5d5942c6755ffa4da2c144d0f6ad",
        "historical_evidence_modified": False,
        "phase_boundary": "Phase A only; LOCAL-VERIFY-003 and LOCAL-VERIFY-004 not started.",
        "execution": {
            "fixture_count": 14,
            "checker_rows_executed": 28,
            "runtime_rows_executed": 56,
            "fresh_process_checker_commands": 56,
            "fresh_process_runtime_commands": 112,
            "harness_checks": 195,
            "failed_harness_checks": 0,
            "negative_controls": 11,
            "failed_negative_controls": 0,
        },
        "checker_scope": {
            "mypy_1.19.1": "CHECKER_CONFIRMED",
            "mypy_2.3.1": "NOT_TESTED",
            "pyright_1.1.414": "NOT_TESTED",
        },
        "preserved_failed_preflight": "RAW/PREFLIGHT-FAILURE-20261104T215119Z.json",
        "network_access": False,
        "downloads": False,
        "npm_or_npx_invoked": False,
        "sofa_mutations": False,
        "manifest_scope": "files covers every collection file except ARCHIVE.json and SHA256SUMS.txt; SHA256SUMS covers ARCHIVE.json and every other file except itself.",
        "file_count_excluding_metadata": len(payload),
        "files": payload,
    }
    ARCHIVE.write_text(json.dumps(archive, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ledger_files = regular_files(include_archive=True)
    LEDGER.write_text(
        "".join(
            f"{sha256(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n"
            for path in ledger_files
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "archive_files": len(payload),
        "ledger_files": len(ledger_files),
        "archive_sha256": sha256(ARCHIVE.read_bytes()),
        "ledger_sha256": sha256(LEDGER.read_bytes()),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
