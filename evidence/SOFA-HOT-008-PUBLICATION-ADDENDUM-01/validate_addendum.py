#!/usr/bin/env python3
"""Validate the archived publication addendum against PR #16's frozen drafts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]
EVENT = ROOT / "SOURCE-EVENT"
DRAFTS = REPOSITORY / "evidence/SOFA-HOT-008/RECONCILIATION/SOFA-DRAFTS"
SIGNATURE = "More edge case Gremlins for the Goblin God!"
EXPECTED = {
    "04": ("CASE-04-discord-parser.md", "5d942dc5-a57e-4671-804a-3a825afd3f80"),
    "05": ("CASE-05-openpyxl.md", "6f977ba0-b147-4798-a9fe-a7d73ee10bc3"),
    "06": ("CASE-06-genericalias.md", "546d5c81-c410-4a3f-8520-1a504658ad2e"),
    "08": ("CASE-08-spn2.md", "22e71c43-88e5-4598-8699-7ca07b8e3610"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    authorization = json.loads((EVENT / "OWNER-AUTHORIZATION.json").read_text())
    event = json.loads((EVENT / "PUBLICATION-EVENT.json").read_text())
    approved = {item["case"]: item for item in authorization["drafts"]}
    outcomes = {item["case"]: item for item in event["cases"]}
    assert set(approved) == set(EXPECTED) == set(outcomes)
    assert event["result"] == "FOUR_PUBLISHED_ALL_ACCEPTED_UNDER_ONE_FINAL_LF_RULE"
    assert event["preserved_boundaries"]["pr16_head"] == "bb1eabd27a6606b6c229c32190942bcd9672a261"
    assert event["mutation_counts"]["reply_calls"] == 4
    assert all(event["mutation_counts"][key] == 0 for key in (
        "automatic_retries", "edit_calls", "vote_calls",
        "verification_calls", "delete_calls",
    ))

    source_ledger = {}
    for line in (EVENT / "SHA256SUMS.txt").read_text().splitlines():
        value, relative = line.split("  ", 1)
        assert relative not in source_ledger
        source_ledger[relative] = value
    expected_event_files = {
        path.name for path in EVENT.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    assert set(source_ledger) == expected_event_files
    for relative, value in source_ledger.items():
        assert sha256((EVENT / relative).read_bytes()) == value

    records = []
    for case in sorted(EXPECTED):
        filename, reply_id = EXPECTED[case]
        source_record = approved[case]
        source = (DRAFTS / filename).read_bytes()
        assert len(source) == source_record["bytes"]
        assert sha256(source) == source_record["sha256"]
        assert source.endswith(b"\n") and not source.endswith(b"\n\n")
        assert source[:-1].decode().splitlines()[-1] == SIGNATURE

        outcome = outcomes[case]
        receipt = json.loads((EVENT / outcome["receipt"]).read_text())
        readback = receipt["canonical_readback"]
        published = readback["body"].encode("utf-8")
        assert outcome["reply_id"] == reply_id == readback["reply_id"]
        assert readback["parent_id"] == source_record["post_id"]
        assert readback["lifecycle_state"] == "published"
        assert readback["deleted_at"] is None
        assert readback["final_line"] == SIGNATURE
        assert published == source[:-1]
        assert len(published) == readback["body_bytes"]
        assert sha256(published) == readback["body_sha256"]
        assert receipt["authorization_check"]["other_differences"] == 0
        records.append({
            "case": case,
            "reply_id": reply_id,
            "source_sha256": sha256(source),
            "published_body_sha256": sha256(published),
        })

    print(json.dumps({
        "status": "PASS",
        "case_count": len(records),
        "records": records,
        "network_calls": 0,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
