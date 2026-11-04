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


files = sorted(
    path for path in ROOT.rglob("*")
    if path.is_file()
    and path != LEDGER
    and "__pycache__" not in path.parts
    and ".mypy_cache" not in path.parts
)
lines = [
    "# CODEX-001 finalized evidence integrity ledger",
    "# format: sha256<two spaces>byte_size<two spaces>relative_path",
    "# SHA256SUMS.txt is intentionally excluded: a file cannot contain a stable hash of itself.",
]
for path in files:
    relative = path.relative_to(ROOT).as_posix()
    lines.append(f"{digest(path)}  {path.stat().st_size}  {relative}")
LEDGER.write_text("\n".join(lines) + "\n")
print(f"ledger_entries={len(files)}")
