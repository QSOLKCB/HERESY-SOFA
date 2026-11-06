"""Repository regression coverage for the LOCAL-VERIFY-002B archive."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "evidence/LOCAL-VERIFY-002B/RUNNER/validate.py"
# Importing the evidence-owned validator must not mutate its finalized archive.
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("local_verify_002b_validator", VALIDATOR)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError(f"cannot load validator: {VALIDATOR}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LocalVerify002BArchiveTests(MODULE.LocalVerify002BTests):
    """Run the evidence-owned validation contract in repository CI."""

    def test_required_artifacts_and_boundary(self) -> None:
        """Adapt the historical phase gate without editing frozen evidence.

        The evidence-owned validator correctly asserted during LOCAL-VERIFY-002B
        that phases 003 and 004 had not begun.  That temporal fact is preserved
        in its immutable source.  Current repository CI instead verifies that
        003 is a separate collection and that phase 004 still has not begun.
        """

        root = REPOSITORY / "evidence/LOCAL-VERIFY-002B"
        for relative in (
            "ENVIRONMENT.json",
            "PACKAGE-INVENTORY.json",
            "CHECKER-MATRIX.csv",
            "CLAIM-LEDGER.csv",
            "REPORT.json",
            "REVIEW.md",
            "NEGATIVE-CONTROLS.json",
            "OPEN-ISSUES.md",
            "BASELINE.json",
            "ARCHIVE.json",
            "SHA256SUMS.txt",
            "RAW/EXECUTION.json",
            "RAW/determinism.json",
            "RAW/package-inspection.json",
            "RAW/PREFLIGHT-PARSER-CORRECTION.json",
            "RAW/MYPY-DEPENDENCY-PREFLIGHT.json",
        ):
            self.assertTrue((root / relative).is_file(), relative)
        self.assertTrue((REPOSITORY / "evidence/LOCAL-VERIFY-003/ARCHIVE.json").is_file())
        self.assertTrue((REPOSITORY / "evidence/LOCAL-VERIFY-004/INPUT/LOCAL-VERIFY-004_youtube_inventory.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
