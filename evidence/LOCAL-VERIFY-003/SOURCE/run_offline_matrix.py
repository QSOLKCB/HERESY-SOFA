#!/usr/bin/env python3
"""Execute LOCAL-VERIFY-003's deterministic offline selector campaign."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import socket
import sys
from typing import Any
from unittest.mock import patch


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from broken_first_key import select_first_key  # noqa: E402
from policy_literal import select_literal  # noqa: E402
from reference_oracle import select_reference  # noqa: E402


SEED = 26051105
FIXTURE_PATH = ROOT / "FIXTURES/metadata-fixtures.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic(result: dict[str, Any]) -> tuple[Any, ...]:
    return (
        result["decision"],
        result["origin"],
        result["language"],
        result["reason"],
    )


def choice(result: dict[str, Any]) -> tuple[Any, ...]:
    return result["decision"], result["origin"], result["language"]


def reordered_metadata(metadata: Any) -> list[Any]:
    if not isinstance(metadata, dict):
        return [copy.deepcopy(metadata)]
    fields: list[tuple[str, list[tuple[str, ...]]]] = []
    for field in ("subtitles", "automatic_captions"):
        mapping = metadata.get(field)
        if isinstance(mapping, dict):
            keys = tuple(mapping)
            orders = list(itertools.permutations(keys)) if len(keys) <= 6 else [keys]
            fields.append((field, orders))
    if not fields:
        return [copy.deepcopy(metadata)]
    variants: list[Any] = []
    for orders in itertools.product(*(item[1] for item in fields)):
        variant = copy.deepcopy(metadata)
        for (field, _), order in zip(fields, orders, strict=True):
            source = metadata[field]
            variant[field] = {key: copy.deepcopy(source[key]) for key in order}
        variants.append(variant)
    return variants


class Checks:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def equal(self, check_id: str, actual: Any, expected: Any, *, negative: bool = False) -> None:
        self.items.append(
            {
                "id": check_id,
                "negative_control": negative,
                "passed": actual == expected,
                "actual": actual,
                "expected": expected,
            }
        )

    def true(self, check_id: str, actual: Any, *, negative: bool = False) -> None:
        self.equal(check_id, bool(actual), True, negative=negative)


def run_fixtures(checks: Checks) -> dict[str, Any]:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixtures = document["fixtures"]
    results: list[dict[str, Any]] = []
    permutation_evaluations = 0
    agreements = 0
    mismatches: list[dict[str, Any]] = []
    minimum_counterexamples: list[dict[str, Any]] = []

    for fixture in fixtures:
        fixture_id = fixture["id"]
        oracle = select_reference(fixture["metadata"], fixture["preferred"])
        literal = select_literal(fixture["metadata"], fixture["preferred"])
        expected = fixture["expected"]
        actual_expected = {
            "decision": oracle["decision"],
            "origin": oracle["origin"],
            "language": oracle["language"],
            "reason": oracle["reason"],
            "metadata_available": oracle["outcomes"]["METADATA_AVAILABLE"],
        }
        checks.equal(f"{fixture_id}.oracle_expected", actual_expected, expected)
        checks.equal(
            f"{fixture_id}.download_boundary",
            oracle["outcomes"]["SUBTITLE_DOWNLOADED_AND_VERIFIED"],
            "NOT_TESTED",
        )

        variants = reordered_metadata(fixture["metadata"])
        literal_choices: set[tuple[Any, ...]] = set()
        for index, variant in enumerate(variants):
            variant_oracle = select_reference(variant, fixture["preferred"])
            variant_literal = select_literal(variant, fixture["preferred"])
            checks.equal(
                f"{fixture_id}.oracle_order_{index:03d}",
                variant_oracle,
                oracle,
                negative=len(variants) > 1,
            )
            literal_choices.add(choice(variant_literal))
            permutation_evaluations += 1
        if fixture["literal_order_sensitive"]:
            checks.true(
                f"{fixture_id}.literal_order_sensitivity_detected",
                len(literal_choices) > 1,
                negative=True,
            )

        agrees = choice(literal) == choice(oracle)
        agreements += int(agrees)
        if not agrees:
            mismatch = {
                "fixture_id": fixture_id,
                "category": fixture["category"],
                "literal": literal,
                "oracle": {
                    key: oracle[key]
                    for key in ("decision", "origin", "language", "reason")
                },
                "interpretation": (
                    "The TIL supplies no code; this mismatch is against the preserved "
                    "examiner literal translation and identifies an underspecified rule."
                ),
            }
            mismatches.append(mismatch)
            if fixture["minimum_counterexample"]:
                minimum_counterexamples.append(mismatch)
        results.append(
            {
                "fixture_id": fixture_id,
                "category": fixture["category"],
                "description": fixture["description"],
                "oracle": oracle,
                "literal": literal,
                "agreement": agrees,
                "permutation_count": len(variants),
                "literal_distinct_choices": [list(item) for item in sorted(literal_choices, key=repr)],
            }
        )

    return {
        "fixture_count": len(fixtures),
        "permutation_evaluations": permutation_evaluations,
        "agreement_count": agreements,
        "mismatch_count": len(mismatches),
        "results": results,
        "mismatches": mismatches,
        "minimum_counterexamples": minimum_counterexamples,
    }


def run_broken_controls(checks: Checks) -> dict[str, Any]:
    usable = lambda suffix: [{"url": f"https://captions.invalid/{suffix}"}]
    controls: list[dict[str, Any]] = []

    translated_first = {
        "automatic_captions": {
            "es": usable("B001-es"),
            "en-orig": usable("B001-en-orig"),
        }
    }
    broken_a = select_first_key(translated_first)
    oracle_a = select_reference(translated_first)
    passed = broken_a == ("automatic", "es") and choice(oracle_a) == (
        "SELECT",
        "automatic",
        "en-orig",
    )
    checks.true("B001.first_auto_translation_detected", passed, negative=True)
    controls.append({"id": "B001", "broken": broken_a, "oracle": oracle_a, "passed": passed})

    reversed_auto = {
        "automatic_captions": {
            "en-orig": usable("B002-en-orig"),
            "es": usable("B002-es"),
        }
    }
    broken_b = select_first_key(reversed_auto)
    passed = broken_a != broken_b
    checks.true("B002.first_key_reordering_detected", passed, negative=True)
    controls.append({"id": "B002", "first": broken_a, "reversed": broken_b, "passed": passed})

    manual_tie = {
        "subtitles": {"de": usable("B003-de"), "en": usable("B003-en")}
    }
    broken_c = select_first_key(manual_tie)
    oracle_c = select_reference(manual_tie)
    passed = broken_c is not None and oracle_c["decision"] == "ABSTAIN"
    checks.true("B003.manual_tie_detected", passed, negative=True)
    controls.append({"id": "B003", "broken": broken_c, "oracle": oracle_c, "passed": passed})

    malformed = {
        "subtitles": {"de": []},
        "automatic_captions": {"en": usable("B004-en")},
    }
    broken_d = select_first_key(malformed)
    oracle_d = select_reference(malformed)
    passed = broken_d == ("manual", "de") and choice(oracle_d) == (
        "SELECT",
        "automatic",
        "en",
    )
    checks.true("B004.malformed_track_detected", passed, negative=True)
    controls.append({"id": "B004", "broken": broken_d, "oracle": oracle_d, "passed": passed})

    missing_language = {
        "language": None,
        "original_language": None,
        "subtitles": {"de-DE": usable("B005-de")},
    }
    gate_result = bool(missing_language.get("language"))
    oracle_e = select_reference(missing_language)
    passed = not gate_result and oracle_e["outcomes"]["TRACK_SELECTED"]
    checks.true("B005.language_gate_miss_detected", passed, negative=True)
    controls.append({"id": "B005", "gate_result": gate_result, "oracle": oracle_e, "passed": passed})

    deceptive = {
        "automatic_captions": {
            "fr": [{"name": "English (Original)", "url": "https://captions.invalid/B006-fr"}],
            "en": usable("B006-en"),
        }
    }
    broken_f = select_first_key(deceptive)
    oracle_f = select_reference(deceptive)
    passed = broken_f is not None and oracle_f["decision"] == "ABSTAIN"
    checks.true("B006.deceptive_label_detected", passed, negative=True)
    controls.append({"id": "B006", "broken": broken_f, "oracle": oracle_f, "passed": passed})

    return {"control_count": len(controls), "controls": controls}


def run_seeded_stress(checks: Checks) -> dict[str, Any]:
    rng = random.Random(SEED)
    languages = ["en", "de", "fr", "pt-BR", "pt-PT", "zh-Hant", "en-orig"]
    case_count = 128
    reorder_checks = 0
    selected = 0
    abstained = 0
    for case_index in range(case_count):
        metadata: dict[str, Any] = {}
        for field in ("subtitles", "automatic_captions"):
            chosen = rng.sample(languages, rng.randrange(0, 5))
            mapping: dict[str, Any] = {}
            for language in chosen:
                if rng.randrange(5) == 0:
                    mapping[language] = []
                else:
                    mapping[language] = [
                        {"url": f"https://captions.invalid/stress-{case_index}-{language}"}
                    ]
            metadata[field] = mapping
        hint_mode = rng.randrange(5)
        if hint_mode == 1:
            metadata["language"] = rng.choice(languages[:-1])
        elif hint_mode == 2:
            metadata["original_language"] = rng.choice(languages[:-1])
        elif hint_mode == 3:
            metadata["language"] = "en"
            metadata["original_language"] = "de"
        elif hint_mode == 4:
            metadata["formats"] = [
                {"language": rng.choice(languages[:-1]), "acodec": "aac"}
            ]
        baseline = select_reference(metadata)
        selected += int(baseline["decision"] == "SELECT")
        abstained += int(baseline["decision"] == "ABSTAIN")
        for repeat in range(5):
            variant = copy.deepcopy(metadata)
            for field in ("subtitles", "automatic_captions"):
                items = list(variant[field].items())
                rng.shuffle(items)
                variant[field] = dict(items)
            actual = select_reference(variant)
            checks.equal(
                f"STRESS.{case_index:03d}.{repeat}",
                actual,
                baseline,
                negative=True,
            )
            reorder_checks += 1
    return {
        "seed": SEED,
        "case_count": case_count,
        "reorder_checks": reorder_checks,
        "selected": selected,
        "abstained": abstained,
    }


class QuietLogger:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def debug(self, message: str) -> None:
        self.messages.append({"level": "debug", "message": message})

    def warning(self, message: str) -> None:
        self.messages.append({"level": "warning", "message": message})

    def error(self, message: str) -> None:
        self.messages.append({"level": "error", "message": message})


def run_ytdlp_integration(checks: Checks) -> dict[str, Any]:
    from yt_dlp import YoutubeDL
    from yt_dlp.version import __version__

    network_attempts: list[dict[str, str]] = []

    def blocked(*args: Any, **kwargs: Any) -> None:
        network_attempts.append({"args": repr(args), "kwargs": repr(kwargs)})
        raise AssertionError("network access is forbidden in LOCAL-VERIFY-003")

    def track(label: str) -> list[dict[str, str]]:
        return [{"ext": "vtt", "url": f"https://captions.invalid/{label}"}]

    observations: list[dict[str, Any]] = []

    def process(
        test_id: str,
        params: dict[str, Any],
        manual: dict[str, Any],
        automatic: dict[str, Any],
    ) -> tuple[Any, QuietLogger]:
        logger = QuietLogger()
        complete = {"logger": logger, **params}
        with YoutubeDL(complete) as ydl:
            result = ydl.process_subtitles(test_id, manual, automatic)
        return result, logger

    with (
        patch.object(socket.socket, "connect", blocked),
        patch.object(socket, "create_connection", blocked),
        patch.object(socket, "getaddrinfo", blocked),
    ):
        result, logger = process(
            "Y001",
            {"writesubtitles": True, "writeautomaticsub": False, "subtitleslangs": ["de-DE"]},
            {"de-DE": track("Y001-manual")},
            {},
        )
        actual = result["de-DE"]["url"].endswith("Y001-manual")
        checks.true("Y001.explicit_manual", actual)
        observations.append({"id": "Y001", "passed": actual, "selected": result, "messages": logger.messages})

        result, logger = process(
            "Y002",
            {"writesubtitles": True, "writeautomaticsub": True, "subtitleslangs": ["de-DE"]},
            {"de-DE": track("Y002-manual")},
            {"de-DE": track("Y002-auto")},
        )
        actual = result["de-DE"]["url"].endswith("Y002-manual")
        checks.true("Y002.manual_same_key_precedence", actual)
        observations.append({"id": "Y002", "passed": actual, "selected": result, "messages": logger.messages})

        result, logger = process(
            "Y003",
            {"writesubtitles": False, "writeautomaticsub": True, "subtitleslangs": ["en-orig"]},
            {},
            {"en-orig": track("Y003-auto")},
        )
        actual = result["en-orig"]["url"].endswith("Y003-auto")
        checks.true("Y003.explicit_automatic", actual)
        observations.append({"id": "Y003", "passed": actual, "selected": result, "messages": logger.messages})

        result, logger = process(
            "Y004",
            {"writesubtitles": False, "writeautomaticsub": False},
            {"de": track("Y004-manual")},
            {"en": track("Y004-auto")},
        )
        actual = result is None
        checks.true("Y004.no_write_flags", actual, negative=True)
        observations.append({"id": "Y004", "passed": actual, "selected": result, "messages": logger.messages})

        result, logger = process(
            "Y005",
            {"writesubtitles": True, "writeautomaticsub": False, "subtitleslangs": ["zz"]},
            {"de": track("Y005-manual")},
            {},
        )
        # orderedSet_from_options removes unavailable explicit keys before the
        # later per-language warning branch, so this version returns an empty
        # selection without a warning.  The refusal, not a warning side effect,
        # is the correctness property under test.
        actual = result == {}
        checks.true("Y005.unavailable_explicit_language", actual, negative=True)
        observations.append({"id": "Y005", "passed": actual, "selected": result, "messages": logger.messages})

        english_choices: list[str] = []
        for index, manual in enumerate(
            (
                {"de": track("Y006-de-a"), "en": track("Y006-en-a")},
                {"en": track("Y006-en-b"), "de": track("Y006-de-b")},
            )
        ):
            result, logger = process(
                f"Y006-{index}",
                {"writesubtitles": True, "writeautomaticsub": False},
                manual,
                {},
            )
            english_choices.append(next(iter(result)))
        actual = english_choices == ["en", "en"]
        checks.true("Y006.default_english_priority", actual)
        observations.append({"id": "Y006", "passed": actual, "selected_languages": english_choices})

        first_choices: list[str] = []
        for index, manual in enumerate(
            (
                {"de": track("Y007-de"), "fr": track("Y007-fr")},
                {"fr": track("Y007-fr"), "de": track("Y007-de")},
            )
        ):
            result, logger = process(
                f"Y007-{index}",
                {"writesubtitles": True, "writeautomaticsub": False},
                manual,
                {},
            )
            first_choices.append(next(iter(result)))
        actual = first_choices == ["de", "fr"]
        checks.true("Y007.default_non_english_order_dependence", actual, negative=True)
        observations.append({"id": "Y007", "passed": actual, "selected_languages": first_choices})

        explicit_choices: list[str] = []
        for index, manual in enumerate(
            (
                {"de-DE": track("Y008-de-a"), "fr": track("Y008-fr-a")},
                {"fr": track("Y008-fr-b"), "de-DE": track("Y008-de-b")},
            )
        ):
            result, logger = process(
                f"Y008-{index}",
                {"writesubtitles": True, "writeautomaticsub": False, "subtitleslangs": ["de-DE"]},
                manual,
                {},
            )
            explicit_choices.append(next(iter(result)))
        actual = explicit_choices == ["de-DE", "de-DE"]
        checks.true("Y008.explicit_language_order_invariant", actual, negative=True)
        observations.append({"id": "Y008", "passed": actual, "selected_languages": explicit_choices})

        exception: dict[str, str] | None = None
        try:
            process(
                "Y009",
                {"writesubtitles": True, "writeautomaticsub": False, "subtitleslangs": ["de"]},
                {"de": []},
                {},
            )
        except Exception as exc:  # exact current-version negative control
            exception = {"type": type(exc).__name__, "message": str(exc)}
        actual = exception == {"type": "IndexError", "message": "list index out of range"}
        checks.true("Y009.empty_format_list_rejected", actual, negative=True)
        observations.append({"id": "Y009", "passed": actual, "exception": exception})

    checks.equal("Y010.network_attempt_count", len(network_attempts), 0, negative=True)
    return {
        "version": __version__,
        "scope": "YoutubeDL.process_subtitles with synthetic dictionaries only",
        "evidence_class": "EXECUTED_NATIVE_OFFLINE",
        "not_proved": [
            "extractor output",
            "YouTube -orig semantics",
            "remote subtitle availability",
            "subtitle download",
            "subtitle conversion",
        ],
        "network_attempt_count": len(network_attempts),
        "observations": observations,
    }


def main() -> int:
    checks = Checks()
    fixture_results = run_fixtures(checks)
    broken_controls = run_broken_controls(checks)
    stress = run_seeded_stress(checks)
    ytdlp = run_ytdlp_integration(checks)
    failures = [item for item in checks.items if not item["passed"]]
    negative_controls = [item for item in checks.items if item["negative_control"]]
    output = {
        "campaign": "LOCAL-VERIFY-003",
        "seed": SEED,
        "fixture_source": {
            "path": "FIXTURES/metadata-fixtures.json",
            "sha256": sha256(FIXTURE_PATH),
        },
        "source_hashes": {
            path.name: sha256(path)
            for path in sorted(HERE.glob("*.py"))
        },
        "fixture_results": fixture_results,
        "broken_controls": broken_controls,
        "seeded_stress": stress,
        "yt_dlp_integration": ytdlp,
        "outcome_boundaries": {
            "METADATA_AVAILABLE": "Executed against synthetic metadata validation.",
            "TRACK_SELECTED": "Executed against synthetic metadata and local process_subtitles controls.",
            "SUBTITLE_DOWNLOADED_AND_VERIFIED": "NOT_TESTED; no live URL was authorized.",
        },
        "assertions": {
            "count": len(checks.items),
            "negative_control_count": len(negative_controls),
            "failed_count": len(failures),
            "failures": failures,
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
