#!/usr/bin/env python3
"""Build deterministic integrity metadata for the SOFA-HOT-008 archive."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "ARCHIVE.json"
LEDGER = ROOT / "SHA256SUMS.txt"
EXCLUDED = {ARCHIVE, LEDGER}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main() -> None:
    paths = []
    for path in ROOT.rglob("*"):
        if path in EXCLUDED:
            continue
        if path.is_symlink():
            raise SystemExit(f"symlink not allowed: {path.relative_to(ROOT)}")
        if path.is_file():
            paths.append(path)
        elif not path.is_dir():
            raise SystemExit(f"unexpected file type: {path.relative_to(ROOT)}")
    paths.sort(key=lambda path: path.relative_to(ROOT).as_posix())

    files = []
    for path in paths:
        data = path.read_bytes()
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha256(data),
            "git_blob_sha": git_blob(data),
        })

    archive = {
        "schema_version": 1,
        "case_id": "SOFA-HOT-008",
        "archive_state": "immutable_witnesses_reconciled_with_append_only_publication_event",
        "repository_base_commit": "33d736f2dc8c4e150ea24b6a6be85a41f5247caf",
        "original_identities": {
            "monica_gzip_sha256": "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202",
            "primary_codex_report_sha256": "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229",
            "auxiliary_codex_report_sha256": "f9c61410ac238a0c54f8b8803bf2954df83b585c137d454574b39a15f6bbfcb2",
        },
        "publication": {
            "approved_cases": ["03", "04", "05", "06", "08"],
            "published_reply_ids": ["902f2605-383f-4fc9-b8eb-63e21da55dca"],
            "held_cases": ["04", "05", "06", "08"],
            "state": "partial_one_published_four_held",
            "integrity_finding": "SOFA removed one terminal LF from the approved Case 03 request body; visible text/signature match, byte digest does not.",
        },
        "evidence": {
            "file_count": len(files),
            "manifest_scope": "Every collection file except ARCHIVE.json and SHA256SUMS.txt, which are excluded to avoid self-reference.",
            "witness_execution_policy": "Archived executables are never invoked by archive integrity tests.",
        },
        "limitations": [
            "Real yt-dlp extraction/download, Excel rendering, Discord causality and SPN2 quota semantics remain untested.",
            "Pyright and exact mypy 2.3.1 claims remain unexecuted in the independent Codex environment.",
            "Monica supplied raw SOFA source snapshots for two of eight cases and omitted exact per-case argv/timestamps.",
            "SOFA session telemetry was shared/eventually consistent and is not used to attribute this publication event.",
        ],
        "files": files,
    }
    ARCHIVE.write_text(json.dumps(archive, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    LEDGER.write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in files),
        encoding="utf-8",
    )
    print(json.dumps({"case_id": archive["case_id"], "files": len(files)}, sort_keys=True))


if __name__ == "__main__":
    main()
