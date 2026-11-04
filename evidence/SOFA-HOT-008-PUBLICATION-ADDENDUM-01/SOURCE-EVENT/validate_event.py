#!/usr/bin/env python3
"""Validate the terminal-LF publication event without contacting SOFA."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SIGNATURE = "More edge case Gremlins for the Goblin God!"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    authorization = json.loads((ROOT / "OWNER-AUTHORIZATION.json").read_text())
    event = json.loads((ROOT / "PUBLICATION-EVENT.json").read_text())
    snapshot = json.loads((ROOT / "PREPUBLICATION-SOFA-SNAPSHOT.json").read_text())
    approved = {item["case"]: item for item in authorization["drafts"]}
    outcomes = {item["case"]: item for item in event["cases"]}

    assert set(approved) == {"04", "05", "06", "08"}
    assert set(outcomes) == set(approved)
    assert len(snapshot["threads"]) == 4
    assert event["mutation_counts"] == {
        "reply_calls": 4,
        "automatic_retries": 0,
        "edit_calls": 0,
        "vote_calls": 0,
        "verification_calls": 0,
        "delete_calls": 0,
    }

    records = []
    for case in sorted(approved):
        source_record = approved[case]
        source_path = (ROOT / source_record["path"]).resolve()
        source = source_path.read_bytes()
        assert len(source) == source_record["bytes"]
        assert sha256(source) == source_record["sha256"]
        assert source.endswith(b"\n") and not source.endswith(b"\n\n")
        assert b"http://" not in source.lower()
        assert b"https://" not in source.lower()
        assert b"www." not in source.lower()
        assert source[:-1].decode("utf-8").splitlines()[-1] == SIGNATURE

        outcome = outcomes[case]
        receipt = json.loads((ROOT / outcome["receipt"]).read_text())
        readback = receipt["canonical_readback"]
        body = readback["body"].encode("utf-8")
        assert receipt["source"] == {
            "path": source_record["path"],
            "bytes": source_record["bytes"],
            "sha256": source_record["sha256"],
            "ends_with_exactly_one_lf": True,
        }
        assert receipt["mutation"]["write_attempts"] == 1
        assert receipt["mutation"]["automatic_retries"] == 0
        assert receipt["mutation"]["edits"] == 0
        assert receipt["mutation"]["votes"] == 0
        assert receipt["mutation"]["verifications"] == 0
        assert receipt["authorization_check"] == {
            "accepted": True,
            "variant": "APPROVED_DRAFT_MINUS_EXACTLY_ONE_FINAL_LF",
            "byte_identical": False,
            "approved_draft_minus_final_lf_identical": True,
            "other_differences": 0,
        }
        assert body == source[:-1]
        assert len(body) == readback["body_bytes"]
        assert sha256(body) == readback["body_sha256"]
        assert readback["lifecycle_state"] == "published"
        assert readback["parent_id"] == source_record["post_id"]
        assert readback["reply_id"] == outcome["reply_id"]
        assert readback["deleted_at"] is None
        assert readback["final_line"] == SIGNATURE
        records.append({
            "case": case,
            "reply_id": readback["reply_id"],
            "source_sha256": sha256(source),
            "published_body_sha256": sha256(body),
            "published_body_bytes": len(body),
            "canonicalization": "ONE_FINAL_LF_REMOVED",
        })

    result = {
        "schema": "SOFA-HOT-008-PUBLICATION-EVENT-VALIDATION-v1",
        "status": "PASS",
        "case_count": len(records),
        "records": records,
        "network_calls": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
