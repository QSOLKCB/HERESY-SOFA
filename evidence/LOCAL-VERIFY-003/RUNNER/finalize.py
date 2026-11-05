#!/usr/bin/env python3
"""Finalize LOCAL-VERIFY-003 archive and GNU-compatible checksum ledger."""

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
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def files(excluded: set[Path]) -> list[Path]:
    result: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"symlink is forbidden: {path}")
        if path.is_file() and path not in excluded:
            result.append(path)
    return result


def main() -> int:
    payload = files({ARCHIVE, LEDGER})
    records = []
    for path in payload:
        data = path.read_bytes()
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(data),
                "sha256": sha256(data),
                "git_blob_sha": git_blob(data),
            }
        )
    report = json.loads((ROOT / "REPORT.json").read_text(encoding="utf-8"))
    archive = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-003",
        "archive_state": "offline_caption_selection_evidence_finalized",
        "repository_base_commit": "a8d5b1783d5f5096f00504b99f2276f0a9fbff44",
        "historical_evidence_modified": False,
        "execution": {
            "fixture_count": report["results"]["fixture_count"],
            "selected_count": report["results"]["selected_count"],
            "abstained_count": report["results"]["abstained_count"],
            "assertion_count": report["execution"]["assertion_count"],
            "negative_control_count": report["execution"]["negative_control_count"],
            "failed_assertion_count": report["execution"]["failed_assertion_count"],
            "fresh_process_runs": report["execution"]["fresh_process_runs"],
        },
        "evidence_scope": {
            "synthetic_metadata_selection": "EXECUTED_SYNTHETIC",
            "installed_process_subtitles": "EXECUTED_NATIVE_OFFLINE",
            "live_extractor": "NOT_TESTED",
            "subtitle_download_and_verification": "NOT_TESTED",
            "youtube_orig_semantics": "NOT_TESTED",
        },
        "service_boundary": "No live extractor, media host, subtitle download, credentials, SOFA mutation or third-party test traffic.",
        "manifest_scope": "files lists every collection file except ARCHIVE.json and SHA256SUMS.txt; SHA256SUMS covers ARCHIVE.json and every other file except itself.",
        "file_count_excluding_metadata": len(records),
        "files": records,
    }
    ARCHIVE.write_text(
        json.dumps(archive, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_files = files({LEDGER})
    LEDGER.write_text(
        "".join(
            f"{sha256(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n"
            for path in ledger_files
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
