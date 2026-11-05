# LOCAL-VERIFY-003 — open issues

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
