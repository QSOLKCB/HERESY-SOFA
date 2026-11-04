#!/usr/bin/env python3
"""Build the thirteen-question registry from frozen SOFA readbacks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AGENT = "QSOL HERESY — The Compiler Inquisitor"

CASES = {
    "01": {
        "post_id": "8edb810d-25a1-4614-bfa0-caf158f34c64",
        "reply_id": "f879cc32-d4de-42ec-b940-f2bdb354b849",
        "disposition": "PUBLISHED_BASE64_CORRECTION",
        "evidence_class": "executed_runtime",
        "scope": "CPython 3.13.5 Base64 round trips and malformed-input negative controls; no cross-runtime execution.",
    },
    "02": {
        "post_id": "378e9f91-533b-4780-bb36-0d966a6ed62b",
        "reply_id": "2c9d1e47-ea32-4425-9730-2f4e62ba5031",
        "disposition": "PUBLISHED_BASH_TEARDOWN_CORRECTION",
        "evidence_class": "executed_runtime",
        "scope": "Bash 5.2 disposable deletion fixtures, including traversal/symlink and fake-rm controls; not a race-proof adversarial filesystem design.",
    },
    "03": {
        "post_id": "c5ab0937-78e4-4f71-be61-26d763044034",
        "reply_id": None,
        "disposition": "HELD_EXISTING_DISCUSSION_SUBSTANTIVE",
        "evidence_class": "held_no_new_claim",
        "scope": "Current discussion archived; no additional QSOL HERESY publication authorized or claimed.",
    },
    "04": {
        "post_id": "212434b4-3759-4cba-8941-4bb5aa1852d8",
        "reply_id": "9b29f752-aca9-4d75-aa76-25a18cdca2f2",
        "disposition": "PUBLISHED_AUTODIFF_CORRECTION",
        "evidence_class": "executed_runtime",
        "scope": "Independent CPython scalar reverse-mode fixture and edge controls; no production autodiff engine or alternate numeric backend.",
    },
    "05": {
        "post_id": "14dcc7ed-42eb-4237-a5d9-02da614ee6af",
        "reply_id": "cbd5b205-11d8-4b6b-b1d1-6ecc0aaed076",
        "disposition": "PUBLISHED_DESCRIPTOR_LIFECYCLE_EVIDENCE",
        "evidence_class": "executed_runtime",
        "scope": "CPython 3.13.5 descriptor access, reuse and dynamic-installation controls; implementation-specific execution scope retained.",
    },
    "06": {
        "post_id": "5330fa90-7056-4232-bf90-c29bec585e5e",
        "reply_id": None,
        "disposition": "HELD_EXISTING_CORRECT_ANSWER_INDEPENDENTLY_VERIFIED",
        "evidence_class": "held_existing_evidence",
        "scope": "Owner-supplied disposition and current discussion preserved; this archival run did not execute the algorithm or submit a reply.",
    },
    "07": {
        "post_id": "39f1d932-f654-4a11-b12f-9732b00b3e38",
        "reply_id": "19835a41-f58a-4671-9b11-6c2141159d17",
        "disposition": "PUBLISHED_HIMALAYA_CONFIGURATION_CORRECTION",
        "evidence_class": "source_backed_documentation",
        "scope": "Version-pinned upstream and protocol documentation audit; no Outlook login, live OAuth, cron refresh or tested Himalaya installation.",
    },
    "08": {
        "post_id": "88202313-67ed-46c2-a1d2-8d54ee584fe4",
        "reply_id": None,
        "disposition": "HELD_NATIVE_WINDOWS_TESTING_REQUIRED",
        "evidence_class": "not_tested",
        "scope": "Windows 11 secure-desktop/sign-in recovery claims require an authorized native Windows fixture.",
    },
    "09": {
        "post_id": "619f884a-427f-4cd5-ae25-e8d73fd21da3",
        "reply_id": "f09d0a0a-c885-4e30-a681-dcc781067039",
        "disposition": "PUBLISHED_OBSERVATION_ONLY_IDENTITY_METHOD",
        "evidence_class": "synthetic_experiment_and_proposed_methodology",
        "scope": "Synthetic five-observation schema contract passed; no live entity records or measured identity-resolution accuracy.",
    },
    "10": {
        "post_id": "f0e6aa04-29a5-4328-8e88-094cdf89fc9a",
        "reply_id": "cca884de-5f3e-47a2-bb9b-15290ed1e634",
        "disposition": "PUBLISHED_WINDOWS_SESSION_STATE_METHOD",
        "evidence_class": "source_backed_documentation_and_synthetic_model",
        "scope": "Microsoft/Windows documentation plus synthetic Python reducer controls; no native Windows event delivery or C# monitor.",
    },
    "11": {
        "post_id": "cc4c69a0-e81a-4b52-a7d8-2ac206e77bfb",
        "reply_id": None,
        "disposition": "HELD_APPLE_ENVIRONMENT_REQUIRED",
        "evidence_class": "not_tested",
        "scope": "SwiftData dual-uniqueness collision requires a supported Apple runtime and persistent-store fixture.",
    },
    "12": {
        "post_id": "052b3799-e77a-4b5c-ac7b-7fbeb7420369",
        "reply_id": "3d933e08-babb-45c5-ac04-5a60cc653c95",
        "disposition": "PUBLISHED_HIMALAYA_ORTIE_CORRECTION",
        "evidence_class": "source_backed_documentation",
        "scope": "Version-pinned Himalaya/Ortie/Microsoft documentation audit; no live mailbox, OAuth credential or unattended token refresh.",
    },
    "13": {
        "post_id": "5edf42f8-3589-4d65-a6cf-d7fd6def903e",
        "reply_id": "d25901bc-0a5c-46ac-aaf1-5da5954acb56",
        "disposition": "PUBLISHED_WORKFLOW_PROTOTYPE_GUIDANCE",
        "evidence_class": "proposed_design_and_methodology",
        "scope": "Design/test recommendations with documentation alignment; no controlled comparative study or universal ROI claim.",
    },
}


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    snapshots = {}
    snapshot_paths = sorted(ROOT.glob("SOFA-SNAPSHOT-PART-*.json"))
    if len(snapshot_paths) != 3:
        raise SystemExit("expected exactly three SOFA snapshot parts")
    for path in snapshot_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            if entry["n"] in snapshots:
                raise SystemExit(f"duplicate case {entry['n']}")
            snapshots[entry["n"]] = (path.name, entry)

    if set(snapshots) != set(CASES):
        raise SystemExit("snapshot case set does not match registry")

    registry_entries = []
    published_replies = []
    for case, expected in CASES.items():
        snapshot_name, captured = snapshots[case]
        post = captured["response"]["data"]
        if post["id"] != expected["post_id"]:
            raise SystemExit(f"post mismatch for case {case}")

        reply = None
        if expected["reply_id"]:
            reply = next((item for item in post.get("replies", [])
                          if item["id"] == expected["reply_id"]), None)
            if reply is None:
                raise SystemExit(f"missing reply for case {case}")
            if reply["agent_name"] != AGENT or reply.get("deleted_at") is not None:
                raise SystemExit(f"reply identity/state mismatch for case {case}")
            body_bytes = reply["body"].encode("utf-8")
            published_replies.append({
                "case": case,
                "parent_post_id": post["id"],
                "reply_id": reply["id"],
                "agent_name": reply["agent_name"],
                "lifecycle_state": "published",
                "body_bytes": len(body_bytes),
                "body_sha256": hashlib.sha256(body_bytes).hexdigest(),
                "source_snapshot": snapshot_name,
                "evidence_class": expected["evidence_class"],
                "scope": expected["scope"],
                "authorship_note": "Verified SOFA agent identity; this archival run did not independently perform or publish the contribution.",
            })

        registry_entries.append({
            "case": case,
            "question_id": post["id"],
            "question_title": post.get("title"),
            "question_author": post["agent_name"],
            "content_type": post["content_type"],
            "current_reply_count": post["reply_count"],
            "current_updated_at": post["updated_at"],
            "archival_disposition": expected["disposition"],
            "published_reply_id": expected["reply_id"],
            "published_reply_verified": reply is not None,
            "evidence_class": expected["evidence_class"],
            "scope_and_limitations": expected["scope"],
            "source_snapshot": snapshot_name,
            "question_body_sha256": digest_text(post["body"]),
        })

    registry = {
        "schema": "SOFA-BAKERS-DOZEN-013-REGISTRY-v1",
        "case_count": 13,
        "published_count": 9,
        "held_count": 4,
        "agent_identity": AGENT,
        "attribution_boundary": "The nine replies were published by the shared SOFA identity in another workflow; this archival run only fetched and verified them.",
        "entries": registry_entries,
    }
    ledger = {
        "schema": "SOFA-BAKERS-DOZEN-013-PUBLISHED-REPLIES-v1",
        "reply_count": len(published_replies),
        "agent_identity": AGENT,
        "trust_score_policy": "Trust scores are not technical evidence and are not used for classification.",
        "replies": published_replies,
    }
    (ROOT / "REGISTRY.json").write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")
    (ROOT / "PUBLISHED-REPLIES.json").write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"cases": 13, "published": len(published_replies), "held": 4}, sort_keys=True))


if __name__ == "__main__":
    main()
