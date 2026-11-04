#!/usr/bin/env python3
"""Create a size inventory and standard SHA-256 ledger without self-reference."""

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/trent/SOFA-HOT-008/RECONCILIATION")
INVENTORY = ROOT / "FINAL-FILE-INVENTORY.json"
LEDGER = ROOT / "SHA256SUMS.txt"
EXTERNAL_ANCHORS = [
    ROOT / "../MONICA-001/SOFA-HOT-008-MONICA-001-evidence.gz",
    ROOT / "../CODEX-001-independent-20261104T162141Z/CODEX-001-REPORT.json",
    ROOT / "../CODEX-001-independent-20261104T162141Z/SHA256SUMS.txt",
    ROOT / "../CODEX-001/CODEX-001-REPORT.json",
    ROOT / "../CODEX-001/SHA256SUMS.txt",
    ROOT / "../CODEX-001/ARTIFACTS.json",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def relative(path: Path) -> str:
    return os.path.relpath(path, ROOT)


def record(path: Path, scope: str) -> dict:
    state = path.stat()
    return {
        "bytes": state.st_size,
        "mode": oct(stat.S_IMODE(state.st_mode)),
        "path": relative(path),
        "scope": scope,
        "sha256": digest(path),
    }


def tree_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if path in {INVENTORY, LEDGER}:
            continue
        if path.is_symlink():
            raise RuntimeError(f"refusing symlink in final evidence: {path}")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise RuntimeError(f"unexpected file type in final evidence: {path}")
    return sorted(files, key=relative)


def main() -> None:
    if INVENTORY.exists() or LEDGER.exists():
        raise SystemExit("refusing to overwrite final inventory or SHA256SUMS.txt")
    for path in EXTERNAL_ANCHORS:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"missing or unsafe external evidence anchor: {path}")

    internal = tree_files()
    inventory = {
        "schema": "SOFA-HOT-008-FINAL-FILE-INVENTORY-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "SHA-256",
        "entries": [record(path, "reconciliation-tree") for path in internal]
        + [record(path, "external-witness-anchor") for path in EXTERNAL_ANCHORS],
        "exclusions": [
            {
                "path": "FINAL-FILE-INVENTORY.json",
                "reason": "self-reference avoided; covered by SHA256SUMS.txt",
            },
            {
                "path": "SHA256SUMS.txt",
                "reason": "checksum ledger self-reference avoided",
            },
        ],
        "verification_command": "cd /home/trent/SOFA-HOT-008/RECONCILIATION && sha256sum -c SHA256SUMS.txt",
    }
    with INVENTORY.open("x", encoding="utf-8") as stream:
        json.dump(inventory, stream, indent=2, sort_keys=True)
        stream.write("\n")

    ledger_files = tree_files() + [INVENTORY] + EXTERNAL_ANCHORS
    # De-duplicate in case a future anchor is placed inside the reconciliation tree.
    unique = {path.resolve(): path for path in ledger_files}
    ordered = sorted(unique.values(), key=relative)
    with LEDGER.open("x", encoding="utf-8") as stream:
        for path in ordered:
            stream.write(f"{digest(path)}  {relative(path)}\n")

    print(json.dumps({
        "inventory_entries": len(inventory["entries"]),
        "ledger_entries": len(ordered),
        "inventory_bytes": INVENTORY.stat().st_size,
        "inventory_sha256": digest(INVENTORY),
        "ledger_bytes": LEDGER.stat().st_size,
        "ledger_sha256": digest(LEDGER),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
