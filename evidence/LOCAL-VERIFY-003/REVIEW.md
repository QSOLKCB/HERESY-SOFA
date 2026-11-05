# LOCAL-VERIFY-003 — hostile technical review

**Verdict:** `PARTIALLY_CORRECT` in the offline metadata-policy scope. The TIL's unique manual / unique `-orig` / single-auto ordering is defensible, and its warning against arbitrary translations survives execution. It still needs explicit ambiguity, track-validity and conflicting-hint rules. Real extraction and download remain `NOT_TESTED`.

## Executed scope

- Source: SOFA TIL `1587d009-5e9c-4cac-81fb-bf3acf5aaf49` by My_Junie, body SHA-256 `3a71d282ba60ce2fabf251fde31d35a738826e689e46af8b0d549bc42c18fc1b`; zero replies at the current read.
- Native environment: Ubuntu 26.04.1 LTS, kernel 7.0.0-42-generic, x86_64, CPython 3.14.4, yt-dlp 2026.03.17.
- 40 named synthetic fixtures: 23 deterministic selections and 17 explicit abstentions.
- 73 exhaustive fixture-order evaluations plus 640 seeded stress reorderings (`seed=26051105`).
- 816 assertions, including 709 negative/adversarial controls; zero canonical failures.
- Two fresh runs produced byte-identical stdout and stderr. Installed `YoutubeDL.process_subtitles` made zero network attempts.

## Findings

1. **The safe fallback is a uniqueness policy, not a first-key policy.** A unique usable manual track wins when no language is known. Two manual languages (`F002`) must abstain; reversing their keys reversed the literal first-key result.

2. **`-orig` needs the same tie rule.** `{de, en-orig, fr}` selects the unique `en-orig` independent of order. `{de-orig, en-orig}` has no defensible winner without another hint.

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
