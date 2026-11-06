#!/usr/bin/env python3
"""Fail-closed, dependency-free validation of immutable browser reconnaissance."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "INPUT"
SOURCE_HASHES = {
    "INPUT/LOCAL-VERIFY-004_youtube_inventory.json": "70cc6b9846dad47c2092820794187e68b68ac5cba8056b97810fe209e4c53abc",
    "INPUT/LOCAL-VERIFY-004_selection_report.md": "1785b6804b41cd2326a9e7050224337d5abf1c6aff10f29e00f4288985e0aadb",
}
ALL_IDS = {
    "p2zo4fuOhgM", "dKp50fVKUtw", "eki6bbbZ7AI", "bGSY2mbC1XI",
    "-425IRSpUNc", "URO2P5jRGQo", "XzLSwYIdhns", "2yxWX2rcAdw",
}
SELECTED = ["dKp50fVKUtw", "-425IRSpUNc", "eki6bbbZ7AI", "p2zo4fuOhgM", "bGSY2mbC1XI"]
NEGATIVE = "eki6bbbZ7AI"


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def verify_inputs(root: Path = ROOT) -> dict:
    """Validate source hashes, all eight observations, and selected-five contract."""
    manifest = (root / "SHA256SUMS.txt").read_text(encoding="ascii")
    expected_manifest = "".join(f"{digest}  {name}\n" for name, digest in sorted(SOURCE_HASHES.items()))
    require(manifest == expected_manifest, "source SHA256SUMS ledger changed")
    for name, digest in SOURCE_HASHES.items():
        path = root / name
        require(path.is_file() and not path.is_symlink(), f"missing/nonregular source: {name}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"source digest mismatch: {name}")
    inventory = json.loads((root / "INPUT/LOCAL-VERIFY-004_youtube_inventory.json").read_bytes())
    report = (root / "INPUT/LOCAL-VERIFY-004_selection_report.md").read_text(encoding="utf-8")
    require(inventory.get("schema_version") == "1.0.0", "unexpected inventory schema")
    require(inventory.get("experiment") == "LOCAL-VERIFY-004", "unexpected experiment")
    require(inventory.get("execution_status") == "NOT_TESTED", "unexpected execution claim")
    require(inventory["channel"]["handle"] == "@trentslade83", "wrong channel")
    require(inventory["method"]["yt_dlp_metadata_extraction"] == "NOT_TESTED", "metadata claim changed")
    require(inventory["method"]["subtitle_downloading"] == "NOT_TESTED", "download claim changed")
    candidates = inventory["candidates"]
    require(len(candidates) == 8, "expected eight inspected candidates")
    by_id = {c["video_id"]: c for c in candidates}
    require(len(by_id) == 8 and set(by_id) == ALL_IDS, "video ID set mismatch/duplicate")
    require(all(re.fullmatch(r"[A-Za-z0-9_-]{11}", k) for k in by_id), "invalid video ID")
    chosen = inventory["selection"]["video_ids_in_rank_order"]
    require(chosen == SELECTED and len(set(chosen)) == 5, "selected-five order mismatch")
    require(inventory["selection"]["positive_count"] == 4, "selected positive count mismatch")
    require(inventory["selection"]["provisional_negative_count"] == 1, "selected negative count mismatch")
    start = datetime.fromisoformat(inventory["observation_window"]["first_recorded_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(inventory["observation_window"]["last_recorded_utc"].replace("Z", "+00:00"))
    require(start.tzinfo is not None and start <= end, "invalid observation window")
    for key, c in by_id.items():
        require(c["video_url"] == "https://www.youtube.com/watch?v=" + key, f"wrong video URL: {key}")
        require(c["exact_title"] and key in report, f"missing title/report ID: {key}")
        require(c["suitability"]["execution_result"] == "NOT_TESTED", f"unexecuted case promoted: {key}")
        require(c["captions"]["actual_extractor_availability"] == "NOT_TESTED", f"extractor claim: {key}")
        require(c["captions"]["content_retrieval"] == "NOT_TESTED", f"content claim: {key}")
        require(c["captions"]["manual_track_confirmation"] == "NOT_TESTED", f"manual caption claim: {key}")
        stamp = datetime.fromisoformat(c["observation_timestamp_utc"].replace("Z", "+00:00"))
        require(stamp.tzinfo is not None and start <= stamp <= end, f"timestamp out of range: {key}")
        if key == NEGATIVE:
            require(c["suitability"]["case_type"] == "negative_provisional", "negative type changed")
            require(c["captions"]["availability_observation"] == "NOT_OFFERED_IN_OBSERVED_UI", "negative UI claim")
            require(c["captions"]["visible_language_options"] == [], "negative has UI tracks")
        else:
            require(c["suitability"]["case_type"] == "positive", f"positive type changed: {key}")
            require(c["captions"]["availability_observation"] == "LISTED_IN_PLAYER_MENU", f"positive UI claim: {key}")
            require(c["captions"]["visible_language_options"] == ["English (auto-generated)"], f"language mismatch: {key}")
            require(any("unavailable" in e.lower() for e in c["evidence"]), f"missing conflicting CC observation: {key}")
        expected_rank = chosen.index(key) + 1 if key in chosen else None
        require(c["suitability"]["selected_top_five"] == (key in chosen), f"selection flag: {key}")
        require(c["suitability"]["selection_rank"] == expected_rank, f"selection rank: {key}")
    return {"archive": "LOCAL-VERIFY-004", "phase": "A", "source_sha256_verified": 2,
            "candidates_validated": len(by_id), "selected_validated": len(chosen),
            "ui_listed_positive": 7, "provisional_negative": 1,
            "yt_dlp_extraction": "NOT_TESTED", "subtitle_download": "NOT_TESTED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="alternate archive root for offline tests")
    args = parser.parse_args()
    try:
        result = verify_inputs(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"LOCAL-VERIFY-004 phase A FAIL: {exc}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
