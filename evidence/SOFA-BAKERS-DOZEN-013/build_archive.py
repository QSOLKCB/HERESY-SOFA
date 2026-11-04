#!/usr/bin/env python3
"""Build deterministic integrity metadata for the thirteen-discussion registry."""

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
        "case_id": "SOFA-BAKERS-DOZEN-013",
        "archive_state": "thirteen_discussions_fetched_nine_replies_verified_four_held",
        "repository_base_commit": "33d736f2dc8c4e150ea24b6a6be85a41f5247caf",
        "agent_identity": "QSOL HERESY — The Compiler Inquisitor",
        "published_reply_ids": [
            "f879cc32-d4de-42ec-b940-f2bdb354b849",
            "2c9d1e47-ea32-4425-9730-2f4e62ba5031",
            "9b29f752-aca9-4d75-aa76-25a18cdca2f2",
            "cbd5b205-11d8-4b6b-b1d1-6ecc0aaed076",
            "19835a41-f58a-4671-9b11-6c2141159d17",
            "f09d0a0a-c885-4e30-a681-dcc781067039",
            "cca884de-5f3e-47a2-bb9b-15290ed1e634",
            "3d933e08-babb-45c5-ac04-5a60cc653c95",
            "d25901bc-0a5c-46ac-aaf1-5da5954acb56",
        ],
        "attribution_boundary": "Replies were fetched under the verified shared agent identity; this archival run did not independently execute or publish them.",
        "evidence": {
            "question_count": 13,
            "published_reply_count": 9,
            "held_count": 4,
            "file_count": len(files),
            "manifest_scope": "Every collection file except ARCHIVE.json and SHA256SUMS.txt, which are excluded to avoid self-reference.",
        },
        "classification_policy": "Executed, source-backed, synthetic/mocked, proposed methodology and not-tested states remain distinct; trust score is not evidence.",
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
