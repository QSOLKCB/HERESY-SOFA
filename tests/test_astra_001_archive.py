"""Byte-exact, offline-only contract for Astra's LOCAL-VERIFY-004 preflight."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1] / "evidence" / "LOCAL-VERIFY-004" / "ASTRA-001"
FILES = {
    "ASTRA-001-EXECUTION.json": ("1929997b02c8c1832ac6ba916472bff0caf8eaf3696b296eadfbf6600c86397a", 18820),
    "ASTRA-001-REVIEW.md": ("7fda4f23def3bd7b53a55779b4718ff8d7bff80fbbbeac88f7f21663e5b5530b", 7263),
}
MANIFEST = "ASTRA-001-SHA256SUMS.txt"
MANIFEST_SHA256 = "b046db5e7564813a203942a94a874189fa546e82d8112ee5e6e27249d705c855"
MANIFEST_BYTES = (
    "1929997b02c8c1832ac6ba916472bff0caf8eaf3696b296eadfbf6600c86397a  ASTRA-001-EXECUTION.json\n"
    "7fda4f23def3bd7b53a55779b4718ff8d7bff80fbbbeac88f7f21663e5b5530b  ASTRA-001-REVIEW.md\n"
).encode("ascii")


def read_regular_bytes(path: Path) -> bytes:
    """Read one opened regular file; reject symlinks, FIFOs and descriptor swaps."""
    if path.is_symlink():
        raise ValueError(f"ASTRA-001 missing or nonregular artifact: {path.name}")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"ASTRA-001 missing or nonregular artifact: {path.name}") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"ASTRA-001 missing or nonregular artifact: {path.name}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def audit(root: Path = ROOT) -> dict:
    """Refuse any byte drift before interpreting status; never rewrite the witness."""
    if {p.name for p in root.iterdir()} != set(FILES) | {MANIFEST}:
        raise ValueError("ASTRA-001 artifact membership mismatch")
    manifest = read_regular_bytes(root / MANIFEST)
    if manifest != MANIFEST_BYTES or hashlib.sha256(manifest).hexdigest() != MANIFEST_SHA256:
        raise ValueError("ASTRA-001 checksum manifest mismatch")
    verified = {}
    for name, (digest, size) in FILES.items():
        raw = read_regular_bytes(root / name)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"ASTRA-001 source byte mismatch: {name}")
        verified[name] = raw
    # Parse precisely the receipt bytes already hashed, never re-open the pathname.
    receipt = json.loads(verified["ASTRA-001-EXECUTION.json"])
    if not isinstance(receipt, dict):
        raise ValueError("ASTRA-001 receipt is not an object")
    return receipt


class Astra001ArchiveTests(unittest.TestCase):
    def test_frozen_inputs_and_checksum_manifest(self):
        receipt = audit()
        self.assertEqual(receipt["witness_receipt"], "ASTRA-001")

    def test_preflight_failure_does_not_claim_extraction(self):
        receipt = audit()
        self.assertEqual(receipt["overall_status"], "PREFLIGHT_FAILED")
        self.assertEqual(receipt["failure"]["classification"], "REQUIRED_EXECUTABLE_UNAVAILABLE")
        self.assertEqual(receipt["failure"]["stage"], "offline_preflight")
        self.assertEqual(receipt["live_execution_status"], "NOT_TESTED")
        self.assertEqual(receipt["stage_status"]["stage_2_live_execution"], "NOT_TESTED")
        self.assertEqual(receipt["stage_status"]["stage_3_live_evidence_reconciliation"], "NOT_TESTED")
        self.assertEqual(receipt["stage_status"]["required_executable"], "FAILED")

    def test_no_live_attempts_or_captions_claimed(self):
        r = audit()["live_evidence"]
        self.assertIs(r["phase_b_runner_invoked"], False)
        self.assertEqual(r["extractor_metadata_attempt_count"], 0)
        self.assertEqual(r["subtitle_attempt_count"], 0)
        self.assertEqual(r["metadata_retrieval"], "NOT_TESTED")
        self.assertEqual(r["subtitle_download"], "NOT_TESTED")
        self.assertEqual(r["webvtt_structure"], "NOT_TESTED")
        self.assertEqual(r["metadata_sha256"], "NOT_TESTED")

    def test_target_and_source_are_the_frozen_scope(self):
        receipt = audit()
        self.assertEqual(receipt["target"]["video_id"], "dKp50fVKUtw")
        self.assertEqual(receipt["preflight"]["source"]["requested_ref"], "783608c3449689c0c61b7ab4be9c07ce1f1b61d8")
        self.assertEqual(receipt["preflight"]["source"]["returned_commit_sha"], "783608c3449689c0c61b7ab4be9c07ce1f1b61d8")
        self.assertEqual(receipt["browser_comparison"]["comparison_status"], "NOT_TESTED")

    def test_mutated_receipt_rejected_without_touching_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "ASTRA-001"
            shutil.copytree(ROOT, staged)
            p = staged / "ASTRA-001-EXECUTION.json"
            p.write_bytes(p.read_bytes().replace(b'"PREFLIGHT_FAILED"', b'"PASSED"', 1))
            with self.assertRaisesRegex(ValueError, "source byte mismatch"):
                audit(staged)
        self.assertEqual(audit()["overall_status"], "PREFLIGHT_FAILED")

    def test_mutated_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "ASTRA-001"
            shutil.copytree(ROOT, staged)
            (staged / MANIFEST).write_bytes(b"not the approved manifest\n")
            with self.assertRaisesRegex(ValueError, "checksum manifest mismatch"):
                audit(staged)

    def test_symlinked_manifest_rejected_even_when_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "ASTRA-001"
            shutil.copytree(ROOT, staged)
            outside = Path(tmp) / "approved-manifest-copy"
            outside.write_bytes((staged / MANIFEST).read_bytes())
            (staged / MANIFEST).unlink()
            (staged / MANIFEST).symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "nonregular artifact"):
                audit(staged)
        self.assertEqual(audit()["overall_status"], "PREFLIGHT_FAILED")

    def test_verified_receipt_bytes_are_not_read_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "ASTRA-001"
            shutil.copytree(ROOT, staged)
            original_reader = read_regular_bytes
            receipt_reads = []

            def mutate_after_read(path):
                raw = original_reader(path)
                if path.name == "ASTRA-001-EXECUTION.json":
                    receipt_reads.append(path)
                    # Replace the pathname after verified bytes were obtained.
                    path.write_bytes(b'{"overall_status": "PASSED"}')
                return raw

            with mock.patch(__name__ + ".read_regular_bytes", side_effect=mutate_after_read):
                receipt = audit(staged)
            self.assertEqual(receipt["overall_status"], "PREFLIGHT_FAILED")
            self.assertEqual(len(receipt_reads), 1)
            with self.assertRaisesRegex(ValueError, "source byte mismatch"):
                audit(staged)
        self.assertEqual(audit()["overall_status"], "PREFLIGHT_FAILED")


if __name__ == "__main__":
    unittest.main()
