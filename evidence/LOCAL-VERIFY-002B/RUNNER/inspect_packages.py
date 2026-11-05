#!/usr/bin/env python3
"""Validate the two pinned checker distributions and safely unpack Pyright.

This deliberately does not invoke pip, uv, npm, npx, or package lifecycle
scripts.  It accepts only the exact LOCAL-VERIFY-002B package identities.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
from email.parser import BytesParser
from email.policy import default
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
from typing import Any
import zipfile


MYPY_FILENAME = (
    "mypy-2.3.1-cp314-cp314-manylinux2014_x86_64."
    "manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"
)
PYRIGHT_FILENAME = "pyright-1.1.414.tgz"
MAX_MEMBERS = 20_000
MAX_MEMBER_BYTES = 200 * 1024 * 1024
MAX_TOTAL_BYTES = 750 * 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member_name(name: str) -> PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe archive member spelling: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe archive member path: {name!r}")
    if re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"drive-qualified archive member: {name!r}")
    return path


def check_bounds(count: int, total: int, size: int, name: str) -> None:
    if count > MAX_MEMBERS:
        raise ValueError(f"member ceiling exceeded at {name!r}")
    if size < 0 or size > MAX_MEMBER_BYTES:
        raise ValueError(f"member size rejected for {name!r}: {size}")
    if total > MAX_TOTAL_BYTES:
        raise ValueError(f"total uncompressed size ceiling exceeded at {name!r}")


def normalized_distribution_name(name: str) -> str:
    """Apply the PyPA comparison normalization for distribution names."""
    return re.sub(r"[-_.]+", "-", name).lower()


def inspect_wheel(
    wheel: Path,
    pypi_json: Path,
    *,
    expected_name: str,
    expected_version: str,
    expected_filename: str,
) -> dict[str, Any]:
    metadata = json.loads(pypi_json.read_text(encoding="utf-8"))
    release = next((item for item in metadata["urls"] if item["filename"] == wheel.name), None)
    if release is None:
        raise ValueError("wheel is absent from official PyPI release metadata")
    actual_size = wheel.stat().st_size
    actual_sha256 = sha256_file(wheel)
    if wheel.name != expected_filename:
        raise ValueError(f"unexpected wheel filename: {wheel.name}")
    if (
        metadata["info"]["name"] != expected_name
        or metadata["info"]["version"] != expected_version
    ):
        raise ValueError(
            f"PyPI metadata identity is not {expected_name} {expected_version}"
        )
    if actual_size != release["size"] or actual_sha256 != release["digests"]["sha256"]:
        raise ValueError("mypy wheel does not match official PyPI size and SHA-256")

    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    record_rows: list[list[str]] | None = None
    dist_metadata: dict[str, Any] | None = None
    wheel_metadata: str | None = None
    with zipfile.ZipFile(wheel) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise ValueError(f"wheel CRC failure: {corrupt}")
        infos = archive.infolist()
        for index, info in enumerate(infos, start=1):
            safe_member_name(info.filename.rstrip("/") if info.is_dir() else info.filename)
            if info.filename in seen:
                raise ValueError(f"duplicate wheel member: {info.filename!r}")
            seen.add(info.filename)
            total += info.file_size
            check_bounds(index, total, info.file_size, info.filename)
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(unix_mode)
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ValueError(f"non-regular wheel member rejected: {info.filename!r}")
            kind = "directory" if info.is_dir() else "regular"
            item: dict[str, Any] = {
                "path": info.filename,
                "type": kind,
                "uncompressed_bytes": info.file_size,
                "compressed_bytes": info.compress_size,
            }
            if not info.is_dir():
                data = archive.read(info)
                item["sha256"] = sha256_bytes(data)
                if info.filename.endswith(".dist-info/RECORD"):
                    record_rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
                elif info.filename.endswith(".dist-info/METADATA"):
                    parsed = BytesParser(policy=default).parsebytes(data)
                    dist_metadata = {
                        "name": parsed["Name"],
                        "version": parsed["Version"],
                        "requires_python": parsed["Requires-Python"],
                        "requires_dist": parsed.get_all("Requires-Dist", []),
                    }
                elif info.filename.endswith(".dist-info/WHEEL"):
                    wheel_metadata = data.decode("utf-8")
            members.append(item)

        if record_rows is None or dist_metadata is None or wheel_metadata is None:
            raise ValueError("wheel lacks RECORD, METADATA, or WHEEL")
        member_by_path = {item["path"]: item for item in members}
        record_verified = 0
        for row in record_rows:
            if len(row) != 3:
                raise ValueError(f"invalid RECORD row: {row!r}")
            path, encoded_digest, encoded_size = row
            if path not in member_by_path:
                raise ValueError(f"RECORD names absent member: {path!r}")
            if not encoded_digest and not encoded_size:
                if not path.endswith(".dist-info/RECORD"):
                    raise ValueError(f"unexpected unhashed RECORD entry: {path!r}")
                continue
            algorithm, encoded = encoded_digest.split("=", 1)
            if algorithm != "sha256":
                raise ValueError(f"unexpected RECORD hash algorithm: {algorithm}")
            raw = archive.read(path)
            expected = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
            if encoded != expected or int(encoded_size) != len(raw):
                raise ValueError(f"RECORD mismatch: {path!r}")
            record_verified += 1

    if (
        normalized_distribution_name(dist_metadata["name"])
        != normalized_distribution_name(expected_name)
        or dist_metadata["version"] != expected_version
    ):
        raise ValueError("wheel METADATA identity mismatch")
    return {
        "filename": wheel.name,
        "bytes": actual_size,
        "sha256": actual_sha256,
        "official_pypi_sha256": release["digests"]["sha256"],
        "official_pypi_size": release["size"],
        "official_url": release["url"],
        "archive_format": "zip/wheel",
        "safety": {
            "accepted": True,
            "member_count": len(members),
            "total_uncompressed_bytes": total,
            "duplicate_paths": 0,
            "absolute_or_traversal_paths": 0,
            "links_devices_fifos": 0,
            "crc_verified": True,
            "record_hashes_verified": record_verified,
            "bounds": {
                "max_members": MAX_MEMBERS,
                "max_member_bytes": MAX_MEMBER_BYTES,
                "max_total_bytes": MAX_TOTAL_BYTES,
            },
        },
        "metadata": dist_metadata,
        "wheel_metadata": wheel_metadata,
        "members": members,
    }


def verify_npm_integrity(path: Path, integrity: str) -> dict[str, str]:
    algorithm, encoded = integrity.split("-", 1)
    if algorithm != "sha512":
        raise ValueError(f"unexpected npm integrity algorithm: {algorithm}")
    expected = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha512(path.read_bytes()).digest()
    if actual != expected:
        raise ValueError("Pyright tarball does not match npm SHA-512 integrity")
    return {"algorithm": algorithm, "base64": encoded, "hex": actual.hex()}


def inspect_and_extract_pyright(
    tarball: Path, registry_json: Path, destination: Path
) -> dict[str, Any]:
    metadata = json.loads(registry_json.read_text(encoding="utf-8"))
    if tarball.name != PYRIGHT_FILENAME:
        raise ValueError(f"unexpected Pyright filename: {tarball.name}")
    if metadata.get("name") != "pyright" or metadata.get("version") != "1.1.414":
        raise ValueError("registry metadata identity is not Pyright 1.1.414")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"extraction destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    pre_sha256 = sha256_file(tarball)
    npm_integrity = verify_npm_integrity(tarball, metadata["dist"]["integrity"])
    sha1 = hashlib.sha1(tarball.read_bytes(), usedforsecurity=False).hexdigest()
    if sha1 != metadata["dist"]["shasum"]:
        raise ValueError("Pyright tarball does not match registry SHA-1")

    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    package_json: dict[str, Any] | None = None
    with tarfile.open(tarball, "r:gz") as archive:
        tar_members = archive.getmembers()
        for index, member in enumerate(tar_members, start=1):
            safe_member_name(member.name.rstrip("/") if member.isdir() else member.name)
            if member.name in seen:
                raise ValueError(f"duplicate tar member: {member.name!r}")
            seen.add(member.name)
            total += member.size
            check_bounds(index, total, member.size, member.name)
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ValueError(f"link/device/FIFO tar member rejected: {member.name!r}")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"unexpected tar member type: {member.name!r}")
            item: dict[str, Any] = {
                "path": member.name,
                "type": "regular" if member.isfile() else "directory",
                "bytes": member.size,
                "mode": oct(member.mode & 0o777),
            }
            if member.isfile():
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read tar member: {member.name!r}")
                data = stream.read()
                if len(data) != member.size:
                    raise ValueError(f"short tar member read: {member.name!r}")
                item["sha256"] = sha256_bytes(data)
                if member.name == "package/package.json":
                    package_json = json.loads(data.decode("utf-8"))
            members.append(item)

        if package_json is None:
            raise ValueError("Pyright package.json is missing")
        if package_json.get("name") != "pyright" or package_json.get("version") != "1.1.414":
            raise ValueError("Pyright package.json identity mismatch")
        forbidden_scripts = {"preinstall", "install", "postinstall"}.intersection(
            package_json.get("scripts", {})
        )
        if forbidden_scripts:
            raise ValueError(f"package lifecycle scripts rejected: {sorted(forbidden_scripts)}")
        if package_json.get("dependencies", {}) != {}:
            raise ValueError(
                f"unexpected Pyright runtime dependencies: {package_json.get('dependencies', {})!r}"
            )
        if package_json.get("optionalDependencies", {}) != {"fsevents": "~2.3.3"}:
            raise ValueError(
                "unexpected Pyright optional dependencies: "
                f"{package_json.get('optionalDependencies', {})!r}"
            )
        if package_json.get("engines", {}).get("node") != ">=14.0.0":
            raise ValueError(f"unexpected Node engine: {package_json.get('engines')!r}")

        # Re-open after the complete validation pass and write only approved
        # regular files/directories beneath the dedicated destination.
        for member in tar_members:
            relative = safe_member_name(member.name.rstrip("/") if member.isdir() else member.name)
            target = destination.joinpath(*relative.parts)
            target.relative_to(destination)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot extract tar member: {member.name!r}")
            with target.open("xb") as output:
                shutil.copyfileobj(stream, output, 1024 * 1024)
            target.chmod(0o755 if member.mode & 0o111 else 0o644)

    post_sha256 = sha256_file(tarball)
    if post_sha256 != pre_sha256:
        raise ValueError("Pyright source tarball changed during inspection")
    return {
        "filename": tarball.name,
        "bytes": tarball.stat().st_size,
        "sha256": pre_sha256,
        "official_tarball_url": metadata["dist"]["tarball"],
        "official_registry_sha1": metadata["dist"]["shasum"],
        "official_registry_integrity": metadata["dist"]["integrity"],
        "verified_integrity": npm_integrity,
        "archive_format": "gzip-compressed tar",
        "safety": {
            "accepted": True,
            "member_count": len(members),
            "total_uncompressed_bytes": total,
            "duplicate_paths": 0,
            "absolute_or_traversal_paths": 0,
            "links_devices_fifos": 0,
            "gzip_and_tar_read_complete": True,
            "controlled_extraction": True,
            "bounds": {
                "max_members": MAX_MEMBERS,
                "max_member_bytes": MAX_MEMBER_BYTES,
                "max_total_bytes": MAX_TOTAL_BYTES,
            },
        },
        "package_json": package_json,
        "dependency_assessment": {
            "runtime_dependencies": package_json.get("dependencies", {}),
            "optional_dependencies": package_json.get("optionalDependencies", {}),
            "linux_runtime_dependency_install_required": False,
            "note": (
                "The shipped package has no runtime dependencies. fsevents is optional "
                "and is not used on this Linux host. No package-manager install was run."
            ),
        },
        "members": members,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mypy-wheel", required=True, type=Path)
    parser.add_argument("--mypy-pypi-json", required=True, type=Path)
    parser.add_argument("--librt-wheel", required=True, type=Path)
    parser.add_argument("--librt-pypi-json", required=True, type=Path)
    parser.add_argument("--ast-serialize-wheel", required=True, type=Path)
    parser.add_argument("--ast-serialize-pypi-json", required=True, type=Path)
    parser.add_argument("--typing-extensions-wheel", required=True, type=Path)
    parser.add_argument("--typing-extensions-pypi-json", required=True, type=Path)
    parser.add_argument("--mypy-extensions-wheel", required=True, type=Path)
    parser.add_argument("--mypy-extensions-pypi-json", required=True, type=Path)
    parser.add_argument("--pathspec-wheel", required=True, type=Path)
    parser.add_argument("--pathspec-pypi-json", required=True, type=Path)
    parser.add_argument("--pyright-tgz", required=True, type=Path)
    parser.add_argument("--pyright-registry-json", required=True, type=Path)
    parser.add_argument("--extract-pyright", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    originals = {
        str(args.mypy_wheel): sha256_file(args.mypy_wheel),
        str(args.mypy_pypi_json): sha256_file(args.mypy_pypi_json),
        str(args.librt_wheel): sha256_file(args.librt_wheel),
        str(args.librt_pypi_json): sha256_file(args.librt_pypi_json),
        str(args.ast_serialize_wheel): sha256_file(args.ast_serialize_wheel),
        str(args.ast_serialize_pypi_json): sha256_file(args.ast_serialize_pypi_json),
        str(args.typing_extensions_wheel): sha256_file(args.typing_extensions_wheel),
        str(args.typing_extensions_pypi_json): sha256_file(args.typing_extensions_pypi_json),
        str(args.mypy_extensions_wheel): sha256_file(args.mypy_extensions_wheel),
        str(args.mypy_extensions_pypi_json): sha256_file(args.mypy_extensions_pypi_json),
        str(args.pathspec_wheel): sha256_file(args.pathspec_wheel),
        str(args.pathspec_pypi_json): sha256_file(args.pathspec_pypi_json),
        str(args.pyright_tgz): sha256_file(args.pyright_tgz),
        str(args.pyright_registry_json): sha256_file(args.pyright_registry_json),
    }
    result = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "decision": "ACCEPTED",
        "mypy": inspect_wheel(
            args.mypy_wheel,
            args.mypy_pypi_json,
            expected_name="mypy",
            expected_version="2.3.1",
            expected_filename=MYPY_FILENAME,
        ),
        "mypy_dependencies": {
            "librt": inspect_wheel(
                args.librt_wheel,
                args.librt_pypi_json,
                expected_name="librt",
                expected_version="0.16.0",
                expected_filename=(
                    "librt-0.16.0-cp314-cp314-manylinux2014_x86_64."
                    "manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"
                ),
            ),
            "ast_serialize": inspect_wheel(
                args.ast_serialize_wheel,
                args.ast_serialize_pypi_json,
                expected_name="ast-serialize",
                expected_version="0.13.1",
                expected_filename=(
                    "ast_serialize-0.13.1-cp39-abi3-manylinux_2_17_x86_64."
                    "manylinux2014_x86_64.whl"
                ),
            ),
            "typing_extensions": inspect_wheel(
                args.typing_extensions_wheel,
                args.typing_extensions_pypi_json,
                expected_name="typing-extensions",
                expected_version="4.15.0",
                expected_filename="typing_extensions-4.15.0-py3-none-any.whl",
            ),
            "mypy_extensions": inspect_wheel(
                args.mypy_extensions_wheel,
                args.mypy_extensions_pypi_json,
                expected_name="mypy-extensions",
                expected_version="1.1.0",
                expected_filename="mypy_extensions-1.1.0-py3-none-any.whl",
            ),
            "pathspec": inspect_wheel(
                args.pathspec_wheel,
                args.pathspec_pypi_json,
                expected_name="pathspec",
                expected_version="1.0.4",
                expected_filename="pathspec-1.0.4-py3-none-any.whl",
            ),
        },
        "pyright": inspect_and_extract_pyright(
            args.pyright_tgz, args.pyright_registry_json, args.extract_pyright
        ),
    }
    after = {path: sha256_file(Path(path)) for path in originals}
    if after != originals:
        raise ValueError("a downloaded source artifact changed during inspection")
    result["source_files_unchanged"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": result["decision"],
        "mypy_sha256": result["mypy"]["sha256"],
        "mypy_members": result["mypy"]["safety"]["member_count"],
        "pyright_sha256": result["pyright"]["sha256"],
        "pyright_members": result["pyright"]["safety"]["member_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
