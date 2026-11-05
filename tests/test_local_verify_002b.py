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


if __name__ == "__main__":
    unittest.main(verbosity=2)
