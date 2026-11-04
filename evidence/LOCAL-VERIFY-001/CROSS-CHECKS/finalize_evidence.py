#!/usr/bin/env python3
"""Create deterministic archive metadata and SHA256SUMS for LOCAL-VERIFY-001."""

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
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if path in excluded:
            continue
        if path.is_symlink():
            raise SystemExit(f"symlink not allowed: {path.relative_to(ROOT)}")
        if path.is_file():
            paths.append(path)
        elif not path.is_dir():
            raise SystemExit(f"unexpected file type: {path.relative_to(ROOT)}")
    return sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix())


def file_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256(data),
        "git_blob_sha": git_blob(data),
    }


def main() -> int:
    files = [file_record(path) for path in regular_files(include_archive=False)]
    archive = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "archive_state": "native_and_offline_simulated_evidence_finalized",
        "repository_base_commit": "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a",
        "historical_evidence_modified": False,
        "execution": {
            "native_runtime_assertions": 18,
            "simulated_scheduler_assertions": 41,
            "total_assertions": 59,
            "negative_controls": 20,
            "failed_assertions": 0,
        },
        "checker_scope": {
            "mypy_1.19.1": "EXECUTED_NATIVE",
            "mypy_2.3.1": "NOT_TESTED",
            "pyright_1.1.414": "NOT_TESTED",
        },
        "service_boundary": "No live Internet Archive, Discord, Microsoft, SOFA mutation or third-party test traffic.",
        "manifest_scope": "files lists every collection file except ARCHIVE.json and SHA256SUMS.txt; SHA256SUMS covers ARCHIVE.json and every other file except itself.",
        "file_count_excluding_metadata": len(files),
        "files": files,
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
        "archive_files": len(files),
        "ledger_files": len(ledger_files),
        "archive_sha256": sha256(ARCHIVE.read_bytes()),
        "ledger_sha256": sha256(LEDGER.read_bytes()),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
