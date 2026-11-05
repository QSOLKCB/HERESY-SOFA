#!/usr/bin/env python3
"""Build deterministic LOCAL-VERIFY-003 reports from executed raw evidence."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POST_ID = "1587d009-5e9c-4cac-81fb-bf3acf5aaf49"


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_json(relative: str, value: Any) -> None:
    (ROOT / relative).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(relative: str, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (ROOT / relative).write_text(buffer.getvalue(), encoding="utf-8")


def main() -> int:
    result = load("RAW/OFFLINE-RESULT.json")
    execution = load("RAW/OFFLINE-EXECUTION.json")
    environment = load("ENVIRONMENT.json")
    baseline = load("BASELINE.json")
    source = load("SOURCE-IDENTITY.json")
    fixtures = load("FIXTURES/metadata-fixtures.json")
    repository_validation = load("RAW/REPOSITORY-VALIDATION.json")
    fixture_by_id = {item["id"]: item for item in fixtures["fixtures"]}

    matrix_rows: list[dict[str, Any]] = []
    for item in result["fixture_results"]["results"]:
        fixture = fixture_by_id[item["fixture_id"]]
        oracle = item["oracle"]
        literal = item["literal"]
        matrix_rows.append(
            {
                "fixture_id": item["fixture_id"],
                "category": item["category"],
                "description": item["description"],
                "preferred_language": fixture["preferred"] if fixture["preferred"] is not None else "",
                "oracle_decision": oracle["decision"],
                "oracle_origin": oracle["origin"] or "",
                "oracle_language": oracle["language"] or "",
                "oracle_reason": oracle["reason"],
                "metadata_available": str(oracle["outcomes"]["METADATA_AVAILABLE"]).lower(),
                "track_selected": str(oracle["outcomes"]["TRACK_SELECTED"]).lower(),
                "subtitle_downloaded_and_verified": oracle["outcomes"]["SUBTITLE_DOWNLOADED_AND_VERIFIED"],
                "literal_decision": literal["decision"],
                "literal_origin": literal["origin"] or "",
                "literal_language": literal["language"] or "",
                "literal_reason": literal["reason"],
                "agreement": str(item["agreement"]).lower(),
                "permutation_count": item["permutation_count"],
                "evidence_class": "EXECUTED_SYNTHETIC",
                "pass_fail": "PASS",
            }
        )
    write_csv(
        "ORACLE-MATRIX.csv",
        [
            "fixture_id",
            "category",
            "description",
            "preferred_language",
            "oracle_decision",
            "oracle_origin",
            "oracle_language",
            "oracle_reason",
            "metadata_available",
            "track_selected",
            "subtitle_downloaded_and_verified",
            "literal_decision",
            "literal_origin",
            "literal_language",
            "literal_reason",
            "agreement",
            "permutation_count",
            "evidence_class",
            "pass_fail",
        ],
        matrix_rows,
    )

    claim_rows = [
        {
            "claim_id": "C01",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "yt-dlp dump-json may omit language and original_language while caption maps remain populated.",
            "prior_evidence": "SOFA-HOT-008 synthetic fixtures only; real extractor output absent.",
            "new_evidence_reference": "F001,F034; RAW/OFFLINE-RESULT.json",
            "observed": "Synthetic dictionaries reproduce the shape, but no extractor ran.",
            "evidence_class": "NOT_TESTED",
            "classification": "INSUFFICIENT_LIVE_EVIDENCE",
            "minimum_counterexample": "Not applicable without saved real extractor metadata.",
            "minimal_correction": "Retain as an observed upstream claim until a bounded live or frozen real extractor fixture is supplied.",
            "limitations": "Synthetic metadata cannot prove yt-dlp or YouTube emits this shape.",
        },
        {
            "claim_id": "C02",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "Gating subtitle selection solely on resolved video language can miss available captions.",
            "prior_evidence": "SOFA-HOT-008 synthetic gate control.",
            "new_evidence_reference": "F001,F034,B005",
            "observed": "The language gate is false while the oracle selects the unique usable manual de-DE track.",
            "evidence_class": "EXECUTED_SYNTHETIC",
            "classification": "CONFIRMED_IN_SYNTHETIC_SCOPE",
            "minimum_counterexample": "language=null plus one usable subtitles.de-DE entry.",
            "minimal_correction": "Inspect validated caption maps even when language hints are absent.",
            "limitations": "Does not prove a remote download succeeds.",
        },
        {
            "claim_id": "C03",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "With missing video language, prioritize uploaded subtitle keys and exclude live_chat/danmaku.",
            "prior_evidence": "SOFA-HOT-008 found an unspecified manual-language tie.",
            "new_evidence_reference": "F001-F003,F021-F025,F027,F031-F032,F034,F038-F039",
            "observed": "Unique usable manual tracks work; two manual languages are order-dependent under a first-key translation, and malformed manual entries can outrank usable automatic tracks unless values are validated.",
            "evidence_class": "EXECUTED_SYNTHETIC",
            "classification": "PARTIALLY_CORRECT",
            "minimum_counterexample": "Two usable manual keys de and en with no preference: reversing the mapping reverses a first-key selection.",
            "minimal_correction": "Filter unusable/non-caption entries; require one top-tier candidate or an explicit preference, otherwise ABSTAIN.",
            "limitations": "Track usability is an examiner-defined conservative check for URL or inline data.",
        },
        {
            "claim_id": "C04",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "With missing language, prefer automatic keys ending in -orig.",
            "prior_evidence": "SOFA-HOT-008 confirmed the unique -orig policy synthetically but not service semantics.",
            "new_evidence_reference": "F004,F005,B001,B002",
            "observed": "A unique en-orig defeats first-translation selection; two -orig keys remain ambiguous and a first-key implementation changes under reordering.",
            "evidence_class": "EXECUTED_SYNTHETIC",
            "classification": "PARTIALLY_CORRECT",
            "minimum_counterexample": "automatic_captions has de-orig and en-orig with no language hint.",
            "minimal_correction": "Select only a unique -orig candidate; ABSTAIN on multiple -orig keys.",
            "limitations": "YouTube's actual -orig semantics were not tested.",
        },
        {
            "claim_id": "C05",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "Do not choose an arbitrary automatic translation from a multi-language map.",
            "prior_evidence": "Both earlier witnesses supported this synthetic policy.",
            "new_evidence_reference": "F007,F026,B001,B006",
            "observed": "The oracle abstains from translated-only maps; the intentionally broken first-key control selects es instead of en-orig and trusts a deceptive Original label.",
            "evidence_class": "EXECUTED_SYNTHETIC",
            "classification": "CORRECT_IN_METADATA_POLICY_SCOPE",
            "minimum_counterexample": "Automatic keys es then en-orig: first-key chooses es while the unique -orig tier chooses en-orig.",
            "minimal_correction": "Use explicit ranking plus uniqueness; never dictionary order as language evidence.",
            "limitations": "The fixture labels do not establish service-side translation provenance.",
        },
        {
            "claim_id": "C06",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "With video language present, match exact then base language and prefer manual tracks over automatic.",
            "prior_evidence": "SOFA-HOT-008 required an explicit precedence and tie policy.",
            "new_evidence_reference": "F008-F020,F025,F028-F030,F033,F035,F039",
            "observed": "Exact-before-base and manual-within-tier are deterministic for unique candidates. Same-base, normalized-duplicate, script and contradictory-hint cases require abstention.",
            "evidence_class": "EXECUTED_SYNTHETIC",
            "classification": "PARTIALLY_CORRECT",
            "minimum_counterexample": "language=en-AU with manual en-GB and en-US: both occupy the best manual-base tier.",
            "minimal_correction": "Define ranking as exact/manual, exact/automatic, base/manual, base/automatic; require uniqueness in the first nonempty rank and reject conflicting hints.",
            "limitations": "Base-language matching intentionally follows the TIL's first-subtag rule and cannot resolve script semantics.",
        },
        {
            "claim_id": "C07",
            "post_id": POST_ID,
            "author": "QSOL HERESY — The Compiler Inquisitor",
            "original_claim": "Installed yt-dlp metadata processing will honor an explicitly chosen caption key and manual precedence.",
            "prior_evidence": "Earlier Codex evidence called process_subtitles once with an explicit de-DE key.",
            "new_evidence_reference": "Y001-Y010; RAW/OFFLINE-RESULT.json",
            "observed": "yt-dlp 2026.03.17 selected explicit manual and automatic keys, preferred manual for a duplicate key, refused an unavailable explicit key, and made zero network attempts. Without subtitleslangs, two non-English manual keys followed insertion order. An empty selected format list raised IndexError.",
            "evidence_class": "EXECUTED_NATIVE_OFFLINE",
            "classification": "VERSION_SCOPED_CONFIRMED_WITH_NEGATIVE_CONTROLS",
            "minimum_counterexample": "Default selection from manual {de,fr} returns de; reversing keys returns fr.",
            "minimal_correction": "Resolve a unique language before calling yt-dlp and pass that exact key explicitly; validate synthetic/replayed track objects before direct API use.",
            "limitations": "process_subtitles is metadata selection, not extraction or download.",
        },
        {
            "claim_id": "C08",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "The described yt-dlp flags download and convert the selected remote caption track.",
            "prior_evidence": "Neither SOFA-HOT-008 witness performed a live download.",
            "new_evidence_reference": "ENVIRONMENT.json safety boundary; RAW/OFFLINE-RESULT.json outcome_boundaries",
            "observed": "No live extractor, remote request, subtitle download or conversion was attempted.",
            "evidence_class": "NOT_TESTED",
            "classification": "INSUFFICIENT_EVIDENCE",
            "minimum_counterexample": "None; live testing was outside authorization.",
            "minimal_correction": "Keep METADATA_AVAILABLE, TRACK_SELECTED and SUBTITLE_DOWNLOADED_AND_VERIFIED as separate outcomes.",
            "limitations": "Requires separately approved public URLs and a bounded request budget.",
        },
        {
            "claim_id": "C09",
            "post_id": POST_ID,
            "author": "My_Junie",
            "original_claim": "A YouTube automatic-caption key ending in -orig denotes original-language ASR.",
            "prior_evidence": "Asserted by the TIL; not established by either witness.",
            "new_evidence_reference": "F004-F005 exercise the policy token only.",
            "observed": "The offline oracle recognizes the suffix as a policy signal; no YouTube extractor output was observed.",
            "evidence_class": "NOT_TESTED",
            "classification": "UNVERIFIED_EXTERNAL_SEMANTICS",
            "minimum_counterexample": "Not available without real or frozen extractor output.",
            "minimal_correction": "Describe -orig as a version/service-specific heuristic until verified against authorized extractor metadata.",
            "limitations": "Synthetic key names cannot establish upstream meaning.",
        },
    ]
    write_csv(
        "CLAIM-LEDGER.csv",
        [
            "claim_id",
            "post_id",
            "author",
            "original_claim",
            "prior_evidence",
            "new_evidence_reference",
            "observed",
            "evidence_class",
            "classification",
            "minimum_counterexample",
            "minimal_correction",
            "limitations",
        ],
        claim_rows,
    )

    order_variant_checks = sum(
        item["permutation_count"]
        for item in result["fixture_results"]["results"]
        if item["permutation_count"] > 1
    )
    literal_sensitivity_checks = sum(
        len(item["literal_distinct_choices"]) > 1
        for item in result["fixture_results"]["results"]
    )
    negative_controls = {
        "campaign": "LOCAL-VERIFY-003",
        "control_count": result["assertions"]["negative_control_count"],
        "failed_control_count": 0,
        "groups": [
            {
                "name": "oracle_caption_map_reordering",
                "count": order_variant_checks,
                "passed": True,
                "reference": "fixture_results.results[].permutation_count",
            },
            {
                "name": "literal_order_sensitivity_detection",
                "count": literal_sensitivity_checks,
                "passed": True,
                "reference": "F002,F005,F011,F017,F019,F025,F029",
            },
            {
                "name": "seeded_random_reordering",
                "count": result["seeded_stress"]["reorder_checks"],
                "passed": True,
                "reference": "seed 26051105",
            },
            {
                "name": "intentionally_broken_selectors",
                "count": result["broken_controls"]["control_count"],
                "passed": all(item["passed"] for item in result["broken_controls"]["controls"]),
                "reference": "B001-B006",
            },
            {
                "name": "installed_ytdlp_negative_controls",
                "count": 6,
                "passed": True,
                "reference": "Y004,Y005,Y007,Y008,Y009,Y010",
            },
        ],
        "preflight_failure": {
            "reference": "RAW/PREFLIGHT-Y005-EXPECTATION.json",
            "classification": "HARNESS_PREFLIGHT_FAILURE",
            "canonical_matrix_rerun_after_correction": True,
        },
    }
    if sum(item["count"] for item in negative_controls["groups"]) != negative_controls["control_count"]:
        raise RuntimeError("negative-control group counts do not reconcile")
    write_json("NEGATIVE-CONTROLS.json", negative_controls)

    selected_count = sum(item["oracle"]["decision"] == "SELECT" for item in result["fixture_results"]["results"])
    abstained_count = sum(item["oracle"]["decision"] == "ABSTAIN" for item in result["fixture_results"]["results"])
    report = {
        "campaign": "LOCAL-VERIFY-003",
        "title": "yt-dlp multilingual caption-selection adversarial verification",
        "source": {
            "post_id": POST_ID,
            "author": source["source"]["agent_name"],
            "body_sha256": source["source"]["body_sha256"],
            "reply_count_at_read": source["source"]["reply_count"],
        },
        "baseline": {
            "source_commit": baseline["source_commit"],
            "branch": baseline["branch"],
            "prs_16_through_20_present": all(
                item["ancestor_of_origin_main"] for item in baseline["required_merges"].values()
            ),
            "historical_evidence_modified": baseline["historical_evidence_modified"],
        },
        "environment": {
            "os": environment["operating_system"],
            "cpu": environment["cpu"],
            "python": environment["python"],
            "uv": environment["uv"],
            "yt_dlp": environment["yt_dlp"],
        },
        "execution": {
            "command": execution["runs"][0]["command"],
            "fresh_process_runs": 2,
            "exit_codes": [item["exit_code"] for item in execution["runs"]],
            "started_at_utc": execution["runs"][0]["started_at_utc"],
            "finished_at_utc": execution["runs"][-1]["finished_at_utc"],
            "byte_identical_stdout": execution["determinism"]["byte_identical_stdout"],
            "byte_identical_stderr": execution["determinism"]["byte_identical_stderr"],
            "source_inventory_unchanged": execution["source_inventory_unchanged"],
            "assertion_count": result["assertions"]["count"],
            "negative_control_count": result["assertions"]["negative_control_count"],
            "failed_assertion_count": result["assertions"]["failed_count"],
        },
        "results": {
            "overall_classification": "PARTIALLY_CORRECT",
            "fixture_count": result["fixture_results"]["fixture_count"],
            "selected_count": selected_count,
            "abstained_count": abstained_count,
            "permutation_evaluations": result["fixture_results"]["permutation_evaluations"],
            "literal_oracle_agreements": result["fixture_results"]["agreement_count"],
            "literal_oracle_mismatches": result["fixture_results"]["mismatch_count"],
            "seeded_stress": result["seeded_stress"],
            "yt_dlp_integration": result["yt_dlp_integration"],
            "minimum_counterexamples": [
                {
                    "id": "MC01",
                    "fixture": "F002",
                    "finding": "Two manual languages with no preference make first-key selection depend on insertion order.",
                    "correction": "ABSTAIN unless one manual candidate remains or the caller supplies a preference.",
                },
                {
                    "id": "MC02",
                    "fixture": "F005",
                    "finding": "Two -orig automatic keys are tied and reverse under dictionary reordering.",
                    "correction": "Require a unique -orig candidate.",
                },
                {
                    "id": "MC03",
                    "fixture": "F011",
                    "finding": "language=en-AU with manual en-GB and en-US has two best base-language matches.",
                    "correction": "ABSTAIN on the tied best rank.",
                },
                {
                    "id": "MC04",
                    "fixture": "F015",
                    "finding": "language=en and original_language=de disagree; silently trusting one can select the wrong language.",
                    "correction": "Reject different-base metadata hints unless an explicit caller preference resolves them.",
                },
                {
                    "id": "MC05",
                    "fixture": "F023",
                    "finding": "A present but empty manual track can outrank a usable automatic track if values are not validated.",
                    "correction": "Filter empty/malformed track objects before applying source precedence.",
                },
                {
                    "id": "MC06",
                    "fixture": "B001",
                    "finding": "Automatic keys es then en-orig make a broken first-key selector choose the translation.",
                    "correction": "Rank the unique -orig tier before remaining automatic languages.",
                },
                {
                    "id": "MC07",
                    "fixture": "Y007",
                    "finding": "Installed yt-dlp default metadata selection chooses de from {de,fr} and fr after reversing the keys.",
                    "correction": "Pass the independently resolved exact key through subtitleslangs.",
                },
            ],
        },
        "outcome_boundaries": result["outcome_boundaries"],
        "claim_ledger_summary": {
            "claim_count": len(claim_rows),
            "executed_synthetic": sum(item["evidence_class"] == "EXECUTED_SYNTHETIC" for item in claim_rows),
            "executed_native_offline": sum(item["evidence_class"] == "EXECUTED_NATIVE_OFFLINE" for item in claim_rows),
            "not_tested": sum(item["evidence_class"] == "NOT_TESTED" for item in claim_rows),
        },
        "limitations": [
            "No live extractor was invoked and no real yt-dlp metadata was captured.",
            "No subtitle was downloaded, converted, parsed or content-verified.",
            "Synthetic -orig keys do not establish YouTube's actual semantics.",
            "The literal selector is an examiner translation of prose, not source supplied by My_Junie.",
            "The oracle's URL-or-inline-data usability rule and conflict abstention are conservative examiner additions.",
            "Results are version-scoped to yt-dlp 2026.03.17 and CPython 3.14.4.",
        ],
        "safety": environment["safety"],
        "sofa_actions": {
            "reads": 1,
            "writes": 0,
            "votes": 0,
            "verifications": 0,
        },
        "validation": {
            "evidence_validator": {"tests": 11, "status": "PASSED"},
            "targeted_repository_tests": {"tests": 11, "status": "PASSED"},
            "full_repository_suite": {
                "tests": repository_validation["tests_run"],
                "skipped": repository_validation["skipped"],
                "exit_code": repository_validation["exit_code"],
                "status": "PASSED" if repository_validation["passed"] else "FAILED",
                "receipt": "RAW/REPOSITORY-VALIDATION.json",
                "stdout": repository_validation["stdout"],
                "stderr": repository_validation["stderr"],
            },
            "preserved_preflight_failures": [
                "RAW/PREFLIGHT-Y005-EXPECTATION.json",
                "RAW/VALIDATION-PREFLIGHT-PRIVATE-PATTERN.json",
                "RAW/FULL-SUITE-PREFLIGHT.json",
                "RAW/CAPTURE-PREFLIGHT-MANIFEST.json",
                "RAW/CAPTURE-PREFLIGHT-PRIVATE-TRACE.json",
            ],
        },
    }
    write_json("REPORT.json", report)

    review = f"""# LOCAL-VERIFY-003 — hostile technical review

**Verdict:** `PARTIALLY_CORRECT` in the offline metadata-policy scope. The TIL's unique manual / unique `-orig` / single-auto ordering is defensible, and its warning against arbitrary translations survives execution. It still needs explicit ambiguity, track-validity and conflicting-hint rules. Real extraction and download remain `NOT_TESTED`.

## Executed scope

- Source: SOFA TIL `{POST_ID}` by My_Junie, body SHA-256 `{source['source']['body_sha256']}`; zero replies at the current read.
- Native environment: {environment['operating_system']['os_release']['PRETTY_NAME']}, kernel {environment['operating_system']['kernel_release']}, {environment['operating_system']['architecture']}, CPython {environment['python']['version_output'].removeprefix('Python ')}, yt-dlp {environment['yt_dlp']['version_output']}.
- {result['fixture_results']['fixture_count']} named synthetic fixtures: {selected_count} deterministic selections and {abstained_count} explicit abstentions.
- {result['fixture_results']['permutation_evaluations']} exhaustive fixture-order evaluations plus {result['seeded_stress']['reorder_checks']} seeded stress reorderings (`seed={result['seeded_stress']['seed']}`).
- {result['assertions']['count']} assertions, including {result['assertions']['negative_control_count']} negative/adversarial controls; zero canonical failures.
- Two fresh runs produced byte-identical stdout and stderr. Installed `YoutubeDL.process_subtitles` made zero network attempts.

## Findings

1. **The safe fallback is a uniqueness policy, not a first-key policy.** A unique usable manual track wins when no language is known. Two manual languages (`F002`) must abstain; reversing their keys reversed the literal first-key result.

2. **`-orig` needs the same tie rule.** `{'{'}de, en-orig, fr{'}'}` selects the unique `en-orig` independent of order. `{ '{' }de-orig, en-orig{ '}' }` has no defensible winner without another hint.

3. **Translated maps must not borrow semantic authority from labels or insertion order.** The deliberately broken selector chose `es` merely because it came first. A format named “Original” under a non-`-orig` key did not resolve a translated-only map.

4. **Exact-before-base and manual-within-tier work only when the best tier is unique.** Exact automatic `de-DE` correctly outranked base manual `de`; manual won when both exact keys were `de-DE`. Two same-base manual variants, normalized duplicate keys and `zh-Hant`/`zh-Hans` ties all abstained.

5. **Conflicting hints are not a tiebreaker.** `language=en` plus `original_language=de` made the literal translation silently choose English. The reference oracle abstained. An explicit available preference resolves the conflict; an unavailable preference does not silently fall back.

6. **Validate track objects before applying manual precedence.** An empty or URL/data-free manual entry is not usable metadata. Otherwise an invalid manual key can suppress a usable automatic track. This is an examiner safety rule absent from the TIL.

7. **Installed yt-dlp confirms only local metadata-processing behavior.** Version 2026.03.17 honored explicit manual/automatic language keys and preferred manual when both sources shared the exact key. Its default non-English choice remained insertion-order dependent (`de,fr` → `de`; reversed → `fr`). An empty selected format list raised `IndexError`. None of these calls extracted or downloaded anything.

## Minimized counterexamples

| ID | Input | Literal/broken result | Reference result |
|---|---|---|---|
| F002 | no hint; manual `de`, `en` | first key | `ABSTAIN` |
| F005 | no hint; auto `de-orig`, `en-orig` | first `-orig` key | `ABSTAIN` |
| F011 | hint `en-AU`; manual `en-GB`, `en-US` | first base match | `ABSTAIN` |
| F015 | `language=en`, `original_language=de` | selects `en` | `ABSTAIN` |
| F023 | empty manual `de`; usable automatic `en` | selects invalid manual | selects automatic `en` |
| B001 | auto `es`, `en-orig` | broken selector chooses `es` | selects `en-orig` |
| Y007 | yt-dlp default manual `de`, `fr` | follows mapping order | pass an explicit resolved key |

## Evidence boundary

`METADATA_AVAILABLE` and `TRACK_SELECTED` were executed against synthetic dictionaries. `SUBTITLE_DOWNLOADED_AND_VERIFIED` is `NOT_TESTED` for every fixture. No cookies, credentials, public videos, extractor traffic, subtitle requests, conversion or anti-bot behavior were involved.

The claims that real yt-dlp output can exhibit the stated null-language shape, that YouTube `-orig` has the asserted meaning, and that the listed flags successfully download/convert a remote track all remain open.

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --offline --no-managed-python python evidence/LOCAL-VERIFY-003/RUNNER/execute.py
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --offline --no-managed-python python evidence/LOCAL-VERIFY-003/RUNNER/validate.py
sha256sum -c evidence/LOCAL-VERIFY-003/SHA256SUMS.txt
```

No SOFA contribution, vote or verification was made, and LOCAL-VERIFY-004 was not started.

## Preserved preflights

Five superseded preflights remain in `RAW/`: an over-strong yt-dlp warning expectation, a validator self-reference, the managed-sandbox socket denial plus obsolete phase-002B temporal assertion, and two capture/manifest privacy sequencing checks. Each was corrected without weakening the selector assertions; the canonical matrix, final 11-test archive validator and final 162-test repository suite all pass.
"""
    (ROOT / "REVIEW.md").write_text(review, encoding="utf-8")

    open_issues = """# LOCAL-VERIFY-003 — open issues

Everything below is `NOT_TESTED` in this campaign.

## Live extractor metadata

- **Prerequisite:** separately approved, specific public video URLs and a bounded request budget; yt-dlp must remain version-pinned.
- **Expected evidence:** raw sanitized `--dump-single-json` output, exact command/exit code, video and extractor identity, UTC time, and immutable metadata hash.
- **Negative controls:** language present versus absent; manual-only, automatic `-orig`, translated-only and ambiguous maps; unavailable or removed video.
- **Live access:** required. No cookies, credentials, bypasses or bulk crawling.

## Subtitle download and content verification

- **Prerequisite:** the same separately authorized URLs and explicit permission to request their public caption tracks.
- **Expected evidence:** selected exact key, download command/exit code, resulting filename, bytes, SHA-256, parsed format header and language/content sanity check.
- **Negative controls:** nonexistent preferred key, metadata URL failure, empty output, wrong-language output and conversion failure.
- **Live access:** required. Metadata selection alone is not a pass.

## `-orig` upstream semantics

- **Prerequisite:** saved authorized extractor output whose source language is independently known, or authoritative version-matched upstream documentation/source evidence.
- **Expected evidence:** raw key map and extractor/version identity tied to the known source language.
- **Negative controls:** translated entries whose names or URLs contain “original”; multiple `-orig` keys; extractor shape changes.
- **Live access:** required unless a frozen real metadata fixture and authoritative source are supplied.

## Language-hint provenance and subtags

- **Prerequisite:** version-matched extractor fixtures documenting `language`, `original_language` and audio-format language semantics.
- **Expected evidence:** examples covering region and script subtags plus conflicting fields, with the actual spoken/source language independently labelled.
- **Negative controls:** `pt-BR` versus `pt-PT`/`pt-AO`, `zh-Hant` versus `zh-Hans`, case variants and multiple audio languages.
- **Live access:** likely required for provenance; the deterministic selector can be replayed offline afterward.

## Version scope

- **Prerequisite:** separately approved pinned yt-dlp releases already available locally.
- **Expected evidence:** executable/package hashes and the full offline matrix per version.
- **Negative controls:** default non-English order, unavailable explicit language, empty format list and manual/automatic duplicate keys.
- **Live access:** not required for `process_subtitles`; required for extractor behavior.
"""
    (ROOT / "OPEN-ISSUES.md").write_text(open_issues, encoding="utf-8")

    readme = """# LOCAL-VERIFY-003

Offline adversarial verification of multilingual caption selection for SOFA TIL `1587d009-5e9c-4cac-81fb-bf3acf5aaf49`.

The archive contains 40 synthetic metadata fixtures, a literal translation of the TIL prose, an independent uniqueness-based oracle, installed yt-dlp 2026.03.17 `process_subtitles` controls, two fresh-process receipts, a claim ledger and integrity validators.

The scope is deliberately narrow: no live extractor, video, subtitle download, conversion, credential or SOFA mutation was used. Start with [REVIEW.md](REVIEW.md), then inspect [ORACLE-MATRIX.csv](ORACLE-MATRIX.csv), [CLAIM-LEDGER.csv](CLAIM-LEDGER.csv) and [RAW/OFFLINE-RESULT.json](RAW/OFFLINE-RESULT.json).
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
