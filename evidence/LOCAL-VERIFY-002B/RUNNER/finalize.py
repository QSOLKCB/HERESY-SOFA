#!/usr/bin/env python3
"""Finalize LOCAL-VERIFY-002B archive metadata and SHA-256 ledger."""

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
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("utf-8") + data,
        usedforsecurity=False,
    ).hexdigest()


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
    report = json.loads((ROOT / "REPORT.json").read_text(encoding="utf-8"))
    packages = json.loads((ROOT / "PACKAGE-INVENTORY.json").read_text(encoding="utf-8"))
    payload = [record(path) for path in regular_files(include_archive=False)]
    archive = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "archive_state": "missing_static_checker_matrix_completed",
        "repository_source_commit": "1ad645e13277a28ba511cad2f6bd2f5d988894d8",
        "historical_local_verify_002_modified": False,
        "phase_boundary": "LOCAL-VERIFY-002B only; LOCAL-VERIFY-003 and LOCAL-VERIFY-004 not started.",
        "execution": {
            "fixture_count": report["execution"]["fixture_count"],
            "matrix_rows": report["execution"]["matrix_rows"],
            "mypy_rows": report["execution"]["mypy_matrix_rows"],
            "pyright_rows": report["execution"]["pyright_matrix_rows"],
            "fresh_process_checker_commands": report["execution"]["fresh_process_checker_commands"],
            "negative_controls": report["execution"]["negative_control_count"],
            "failed_negative_controls": report["execution"]["failed_negative_control_count"],
            "timeouts": len(report["execution"]["checker_timeouts"]),
            "deterministic": report["execution"]["all_semantic_repeat_pairs_identical"],
        },
        "checker_scope": report["coverage"],
        "package_artifacts": {
            "count": packages["artifact_count"],
            "all_archive_safety_checks_accepted": all(
                item["safety"]["accepted"] for item in packages["artifacts"]
            ),
        },
        "preserved_pre_finalization_events": report["pre_finalization_events"],
        "network_acquisition": True,
        "checker_execution_offline": True,
        "global_installation": False,
        "npm_npx_pnpm_invoked": False,
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
