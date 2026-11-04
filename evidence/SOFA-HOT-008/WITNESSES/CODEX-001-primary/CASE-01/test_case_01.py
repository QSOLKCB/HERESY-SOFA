#!/usr/bin/env python3
import argparse
import importlib.metadata
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from corrected import select_caption
from original_policy import literal_first_policy

SEED = 26051108
TRACK = [{"ext": "vtt", "url": "https://invalid.test/caption"}]


def main(receipt_path):
    random.seed(SEED)
    started = datetime.now(timezone.utc).isoformat()
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        passed = actual == expected
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": passed, "classification": classification})

    check("missing_language_sole_uploaded",
          select_caption({"language": None, "original_language": None,
                          "subtitles": {"de-DE": TRACK}}),
          {"source": "manual", "language": "de-DE", "reason": "sole-manual"})
    check("missing_language_original_asr",
          select_caption({"automatic_captions": {"en-orig": TRACK, "de": TRACK}}),
          {"source": "automatic", "language": "en-orig", "reason": "sole-original-asr"})
    check("missing_language_sole_auto",
          select_caption({"automatic_captions": {"fr": TRACK}}),
          {"source": "automatic", "language": "fr", "reason": "sole-automatic"})
    check("translated_map_abstains",
          select_caption({"automatic_captions": {"en": TRACK, "de": TRACK, "fr": TRACK}}),
          {"source": None, "language": None, "reason": "no-safe-unique-choice"})
    check("non_caption_entries_ignored",
          select_caption({"subtitles": {"live_chat": TRACK, "danmaku": TRACK,
                                         "manifest": {"kind": "not-a-track"}}}),
          {"source": None, "language": None, "reason": "no-safe-unique-choice"})
    check("known_exact_manual_precedes_auto",
          select_caption({"language": "en-US", "subtitles": {"en-US": TRACK},
                          "automatic_captions": {"en-US": TRACK}}),
          {"source": "manual", "language": "en-US", "reason": "known-language"})
    check("known_base_unique",
          select_caption({"original_language": "de", "subtitles": {"de-DE": TRACK}}),
          {"source": "manual", "language": "de-DE", "reason": "known-language"})
    check("known_base_ambiguous_abstains",
          select_caption({"language": "en", "subtitles": {"en-US": TRACK, "en-GB": TRACK}}),
          {"source": None, "language": None, "reason": "no-unique-language-match"})
    check("unique_audio_language_used",
          select_caption({"formats": [{"acodec": "opus", "language": "es"}],
                          "subtitles": {"es-MX": TRACK}}),
          {"source": "manual", "language": "es-MX", "reason": "known-language"})
    check("multiple_audio_languages_abstain",
          select_caption({"formats": [{"acodec": "opus", "language": "en"},
                                       {"acodec": "aac", "language": "de"}],
                          "automatic_captions": {"en": TRACK, "de": TRACK}}),
          {"source": None, "language": None, "reason": "no-safe-unique-choice"})

    a = {"subtitles": {"en": TRACK, "de": TRACK}}
    b = {"subtitles": {"de": TRACK, "en": TRACK}}
    check("smallest_tie_counterexample_literal_policy",
          literal_first_policy(a) == literal_first_policy(b), False)
    check("corrected_tie_is_order_independent",
          select_caption(a) == select_caption(b), True)

    try:
        yt_dlp_version = importlib.metadata.version("yt-dlp")
    except importlib.metadata.PackageNotFoundError:
        yt_dlp_version = None

    receipt = {
        "case": "CASE-01",
        "source_id": "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
        "source_author": "My_Junie",
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_01.py --receipt receipt.json",
        "process_exit_code": 0 if all(item["passed"] for item in checks) else 1,
        "yt_dlp_version": yt_dlp_version,
        "remote_download": {"classification": "NOT_TESTED",
                            "reason": "External subtitle download was prohibited."},
        "checks": checks,
        "conclusion": {
            "classification": "PARTIALLY_CORRECT",
            "executed": "The fallback order works for unique synthetic metadata choices.",
            "defect": "Multiple uploaded or same-base tracks have no tie rule; choosing the first mapping key is insertion-order dependent.",
            "minimal_correction": "Require a unique candidate at each tier or accept an explicit caller preference; otherwise abstain."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-01", "passed": receipt["process_exit_code"] == 0,
                      "checks": len(checks), "remote_download": "NOT_TESTED"}, sort_keys=True))
    return receipt["process_exit_code"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
