#!/usr/bin/env python3
"""Bounded, link-free, traversal-safe ingestion of the discovered Monica gzip."""

import gzip
import hashlib
import io
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

WORKSPACE = Path("/home/trent/SOFA-HOT-008")
ARCHIVE = WORKSPACE / "MONICA-001" / "SOFA-HOT-008-MONICA-001-evidence.gz"
RECON = WORKSPACE / "RECONCILIATION"
EXPECTED_ARCHIVE_SHA256 = "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202"
EXTRACTION_ROOT = RECON / "MONICA-EXTRACTED-cc3d4ae960c6"
RECEIPT = RECON / "MONICA-INGESTION-RECEIPT.json"

MAX_GZIP_UNCOMPRESSED = 64 * 1024 * 1024
MAX_TAR_MEMBERS = 1024
MAX_REGULAR_FILES = 512
MAX_SINGLE_FILE = 32 * 1024 * 1024
MAX_TOTAL_REGULAR_BYTES = 64 * 1024 * 1024
MAX_PATH_CHARS = 512


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_gzip_bounded(path):
    output = bytearray()
    with gzip.open(path, "rb") as stream:
        while True:
            chunk = stream.read(min(1024 * 1024, MAX_GZIP_UNCOMPRESSED + 1 - len(output)))
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > MAX_GZIP_UNCOMPRESSED:
                raise ValueError("gzip uncompressed-size ceiling exceeded")
    return bytes(output)


def member_kind(member):
    if member.isfile():
        return "regular"
    if member.isdir():
        return "directory"
    if member.issym():
        return "symlink"
    if member.islnk():
        return "hardlink"
    if member.ischr():
        return "character_device"
    if member.isblk():
        return "block_device"
    if member.isfifo():
        return "fifo"
    return f"unexpected_type_{member.type!r}"


def validate_name(name, is_directory):
    if not name or "\x00" in name or "\\" in name:
        raise ValueError(f"unsafe member name: {name!r}")
    if len(name) > MAX_PATH_CHARS:
        raise ValueError(f"member path too long: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"absolute/traversal path rejected: {name!r}")
    normalized = path.as_posix()
    if normalized in ("", "."):
        if is_directory:
            return "."
        raise ValueError(f"invalid regular-file path: {name!r}")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"drive-like member path rejected: {name!r}")
    return normalized


def main():
    if RECEIPT.exists() or EXTRACTION_ROOT.exists():
        raise SystemExit("refusing to overwrite an existing ingestion receipt or extraction root")
    if not ARCHIVE.is_file():
        raise SystemExit(f"archive not found: {ARCHIVE}")

    started = datetime.now(timezone.utc).isoformat()
    archive_before = {
        "path": str(ARCHIVE.relative_to(WORKSPACE)),
        "bytes": ARCHIVE.stat().st_size,
        "sha256": sha256_file(ARCHIVE),
        "mode": oct(ARCHIVE.stat().st_mode & 0o777),
        "mtime_ns": ARCHIVE.stat().st_mtime_ns,
    }
    if archive_before["sha256"] != EXPECTED_ARCHIVE_SHA256:
        raise SystemExit("archive hash changed between discovery and ingestion")

    uncompressed = load_gzip_bounded(ARCHIVE)
    gzip_result = {
        "status": "PASS",
        "uncompressed_bytes": len(uncompressed),
        "uncompressed_sha256": sha256_bytes(uncompressed),
    }

    members_inventory = []
    decisions = []
    normalized_seen = set()
    regular_count = 0
    total_regular_bytes = 0

    try:
        tar = tarfile.open(fileobj=io.BytesIO(uncompressed), mode="r:")
    except tarfile.TarError as exc:
        raise SystemExit(f"valid gzip but not a readable tar archive: {exc}")

    with tar:
        members = tar.getmembers()
        if len(members) > MAX_TAR_MEMBERS:
            raise SystemExit("tar member-count ceiling exceeded")

        approved = []
        for index, member in enumerate(members):
            kind = member_kind(member)
            normalized = validate_name(member.name, member.isdir())
            record = {
                "index": index,
                "name": member.name,
                "normalized_name": normalized,
                "kind": kind,
                "size": member.size,
                "mode": oct(member.mode),
                "uid": member.uid,
                "gid": member.gid,
                "linkname": member.linkname,
            }
            members_inventory.append(record)

            if normalized != ".":
                if normalized in normalized_seen:
                    raise SystemExit(f"duplicate normalized member path: {normalized}")
                normalized_seen.add(normalized)

            if kind == "directory":
                decisions.append({"name": member.name, "decision": "SKIP_DIRECTORY_ENTRY"})
                continue
            if kind != "regular":
                raise SystemExit(f"unsafe/unexpected archive member type {kind}: {member.name}")
            if member.size < 0 or member.size > MAX_SINGLE_FILE:
                raise SystemExit(f"member size rejected: {member.name}: {member.size}")
            regular_count += 1
            total_regular_bytes += member.size
            if regular_count > MAX_REGULAR_FILES:
                raise SystemExit("regular-file count ceiling exceeded")
            if total_regular_bytes > MAX_TOTAL_REGULAR_BYTES:
                raise SystemExit("total regular-file size ceiling exceeded")
            approved.append((member, normalized))
            decisions.append({"name": member.name, "decision": "APPROVE_REGULAR_FILE"})

        EXTRACTION_ROOT.mkdir(mode=0o755)
        extracted = []
        for member, normalized in approved:
            relative = PurePosixPath(normalized)
            target = EXTRACTION_ROOT.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                raise SystemExit(f"approved regular member has no stream: {member.name}")
            written = 0
            digest = hashlib.sha256()
            with source, target.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > member.size or written > MAX_SINGLE_FILE:
                        raise SystemExit(f"member expanded beyond declared size: {member.name}")
                    digest.update(chunk)
                    output.write(chunk)
            if written != member.size:
                raise SystemExit(f"member byte count mismatch: {member.name}")
            extracted.append({
                "member_name": member.name,
                "relative_path": relative.as_posix(),
                "bytes": written,
                "sha256": digest.hexdigest(),
                "mode_after_extraction": oct(target.stat().st_mode & 0o777),
            })

    archive_after = {
        "bytes": ARCHIVE.stat().st_size,
        "sha256": sha256_file(ARCHIVE),
        "mode": oct(ARCHIVE.stat().st_mode & 0o777),
        "mtime_ns": ARCHIVE.stat().st_mtime_ns,
    }
    unchanged = archive_after == {
        key: archive_before[key] for key in ("bytes", "sha256", "mode", "mtime_ns")
    }
    if not unchanged:
        raise SystemExit("original archive metadata/content identity changed during ingestion")

    receipt = {
        "schema": "SOFA-HOT-008-MONICA-INGESTION-v1",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_kind": "gzip_compressed_posix_tar",
        "archive_before": archive_before,
        "archive_after": archive_after,
        "archive_byte_identical_and_metadata_stable": unchanged,
        "gzip_integrity": gzip_result,
        "limits": {
            "max_gzip_uncompressed_bytes": MAX_GZIP_UNCOMPRESSED,
            "max_tar_members": MAX_TAR_MEMBERS,
            "max_regular_files": MAX_REGULAR_FILES,
            "max_single_file_bytes": MAX_SINGLE_FILE,
            "max_total_regular_bytes": MAX_TOTAL_REGULAR_BYTES,
        },
        "safety_checks": {
            "duplicate_normalized_paths": "PASS",
            "absolute_paths": "PASS",
            "dotdot_traversal": "PASS",
            "symlinks": "PASS_NONE_PRESENT",
            "hardlinks": "PASS_NONE_PRESENT",
            "devices": "PASS_NONE_PRESENT",
            "fifos": "PASS_NONE_PRESENT",
            "unexpected_types": "PASS_NONE_PRESENT",
            "member_count": len(members_inventory),
            "regular_file_count": regular_count,
            "declared_regular_bytes": total_regular_bytes,
        },
        "members": members_inventory,
        "decisions": decisions,
        "extraction_root": str(EXTRACTION_ROOT.relative_to(WORKSPACE)),
        "extracted_files": extracted,
        "scripts_executed_from_archive": False,
        "status": "ACCEPTED_AND_SAFELY_EXTRACTED",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": receipt["status"],
        "members": len(members_inventory),
        "regular_files": regular_count,
        "bytes": total_regular_bytes,
        "extraction_root": str(EXTRACTION_ROOT),
        "receipt": str(RECEIPT),
        "archive_sha256_after": archive_after["sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
