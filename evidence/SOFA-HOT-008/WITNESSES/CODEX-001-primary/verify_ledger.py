#!/usr/bin/env python3
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "SHA256SUMS.txt"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


checked = 0
for line in LEDGER.read_text().splitlines():
    if not line or line.startswith("#"):
        continue
    expected_hash, expected_size, relative = line.split("  ", 2)
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"missing: {relative}")
    actual_size = path.stat().st_size
    if actual_size != int(expected_size):
        raise SystemExit(f"size mismatch: {relative}")
    if digest(path) != expected_hash:
        raise SystemExit(f"hash mismatch: {relative}")
    checked += 1
print(f"verified_entries={checked}")
