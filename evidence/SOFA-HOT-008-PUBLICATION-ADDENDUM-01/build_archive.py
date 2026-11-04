#!/usr/bin/env python3
"""Build deterministic integrity metadata for the publication addendum."""

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
        "case_id": "SOFA-HOT-008-PUBLICATION-ADDENDUM-01",
        "archive_state": "four_additional_replies_published_with_authorized_final_lf_removal",
        "predecessor_pr": 16,
        "predecessor_head": "bb1eabd27a6606b6c229c32190942bcd9672a261",
        "predecessor_archive_sha256": "7386b1dd858330637b92c6bbdcef3bc3330dd4c100d2956ec942ba222f4174c7",
        "published_reply_ids": [
            "5d942dc5-a57e-4671-804a-3a825afd3f80",
            "6f977ba0-b147-4798-a9fe-a7d73ee10bc3",
            "546d5c81-c410-4a3f-8520-1a504658ad2e",
            "22e71c43-88e5-4598-8699-7ca07b8e3610",
        ],
        "canonicalization": {
            "authorized": "remove exactly one final LF from an approved draft ending in exactly one LF",
            "observed": "all four canonical bodies equal their approved draft minus that final LF",
            "other_differences": 0,
        },
        "mutation_boundary": {
            "reply_calls": 4,
            "automatic_retries": 0,
            "edit_calls": 0,
            "vote_calls": 0,
            "verification_calls": 0,
            "merge_performed": False,
            "pages_deployed": False,
        },
        "evidence": {
            "file_count": len(files),
            "manifest_scope": "Every addendum file except ARCHIVE.json and SHA256SUMS.txt, excluded to avoid self-reference.",
            "source_event_executables": "Only validate_event.py was authored and executed by the custodian; no witness executable is present or invoked.",
        },
        "files": files,
    }
    ARCHIVE.write_text(json.dumps(archive, indent=2, sort_keys=True) + "\n")
    LEDGER.write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in files),
        encoding="utf-8",
    )
    print(json.dumps({"case_id": archive["case_id"], "files": len(files)}, sort_keys=True))


if __name__ == "__main__":
    main()
