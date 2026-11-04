#!/usr/bin/env python3
"""Apply explicit SOFA source attribution to already-generated reports."""

import csv
import hashlib
import io
import json
from pathlib import Path


ROOT = Path("/home/trent/SOFA-HOT-008/RECONCILIATION")
CLAIMS = ROOT / "SOFA-HOT-008-CLAIM-LEDGER.csv"
REPORT = ROOT / "SOFA-HOT-008-DUAL-WITNESS-REPORT.json"
REVIEW = ROOT / "SOFA-HOT-008-DUAL-WITNESS-REVIEW.md"
SNAPSHOT = ROOT / "SOFA-CURRENT-SNAPSHOT.json"


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(post: dict, retrieved_at: str) -> dict:
    return {
        "post_id": post["id"],
        "title": post.get("title"),
        "content_type": post["content_type"],
        "original_author": post["agent_name"],
        "body_sha256": digest_text(post["body"]),
        "retrieved_at_utc": retrieved_at,
        "replies": [
            {
                "id": reply["id"],
                "author": reply["agent_name"],
                "body_sha256": digest_text(reply["body"]),
            }
            for reply in post.get("replies", [])
        ],
    }


def main() -> None:
    snapshot = json.loads(SNAPSHOT.read_text())
    posts = {post["id"]: post for post in snapshot["posts"]}

    with CLAIMS.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or "Original author" in rows[0]:
        raise SystemExit("claim ledger missing or already enriched")

    enriched_rows = []
    for row in rows:
        post = posts[row["Original post ID"]]
        enriched_rows.append({
            "Case ID": row["Case ID"],
            "Original post ID": row["Original post ID"],
            "Original author": post["agent_name"],
            "Original body SHA-256": digest_text(post["body"]),
            "Current reply identities": "; ".join(
                f"{reply['id']} ({reply['agent_name']})"
                for reply in post.get("replies", [])
            ) or "NONE",
            **{key: value for key, value in row.items()
               if key not in {"Case ID", "Original post ID"}},
        })
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(enriched_rows[0]))
    writer.writeheader()
    writer.writerows(enriched_rows)
    CLAIMS.write_text(buffer.getvalue(), encoding="utf-8", newline="")

    report = json.loads(REPORT.read_text())
    identities = {}
    for case in report["cases"]:
        value = identity(posts[case["post_id"]], snapshot["retrieved_at_utc"])
        identities[case["case"]] = value
        case["source_identity"] = value
    report["claim_ledger"] = {
        "path": CLAIMS.relative_to(ROOT).as_posix(),
        "bytes": CLAIMS.stat().st_size,
        "sha256": digest_file(CLAIMS),
    }
    report["source_reconciliation"]["identity_method"] = (
        "Author/reply IDs copied from the frozen SOFA snapshot; body SHA-256 "
        "is over the exact UTF-8 body string returned by SOFA."
    )
    report["source_reconciliation"]["source_identities"] = identities
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    review = REVIEW.read_text()
    for case in report["cases"]:
        heading = f"### Case {case['case']} — {case['subject']}\n\n"
        source_line = (
            f"Original source: `{case['post_id']}` by "
            f"{case['source_identity']['original_author']}; body SHA-256 "
            f"`{case['source_identity']['body_sha256']}`.\n\n"
        )
        if heading not in review:
            raise RuntimeError(f"review heading not found: {case['case']}")
        review = review.replace(heading, heading + source_line, 1)
    REVIEW.write_text(review)

    print(json.dumps({
        "claim_rows": len(enriched_rows),
        "post_identities": len(identities),
        "report_sha256": digest_file(REPORT),
        "review_sha256": digest_file(REVIEW),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
