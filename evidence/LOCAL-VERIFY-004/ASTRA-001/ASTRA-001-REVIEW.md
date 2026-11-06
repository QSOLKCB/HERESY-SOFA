# ASTRA-001 — Phase B preflight blocker

**Disposition: PREFLIGHT FAILED; live extraction and subtitle downloading NOT_TESTED.**

The required `yt-dlp 2026.03.17` executable is unavailable on the execution environment's PATH. A timestamped `bash -lc 'command -v yt-dlp'` probe returned exit code **1**, empty stdout and empty stderr. Python's `shutil.which('yt-dlp')` returned no path, and `importlib.util.find_spec('yt_dlp')` found no module in the active interpreter. No dependency was installed, substituted or upgraded. As instructed, execution stopped before the live stage.

This is an observed local preflight failure, **not a YouTube refusal and not a failed extraction attempt**. No extractor process ran; no extractor exit code, metadata response, caption language keys, signed retrieval URLs or subtitle bytes exist from this attempt.

## Identity and provenance

- Repository: QSOLKCB/HERESY-SOFA.
- Approved source commit: `783608c3449689c0c61b7ab4be9c07ce1f1b61d8`.
- GitHub's read-only connector returned that exact commit, titled “Merge pull request #22 from QSOLKCB/evidence/local-verify-004-phase-a”. Each requested source file was fetched with that exact ref, not a moving branch.
- Read: AGENTS.md; LOCAL-VERIFY-004 README; phase_a.py; phase_b.py; both original INPUT artifacts; SHA256SUMS.txt. All seven local UTF-8 reconstructions matched their returned Git blob SHA-1 identities. This verifies the inspected source subset, not a full local Git checkout or commit-signature validation.
- Target: **Inside the Bureau of Software Anomalies | HERESY-SOFA**, `dKp50fVKUtw`, https://www.youtube.com/watch?v=dKp50fVKUtw, owner-identified channel `@trentslade83`. Current extractor identity remains NOT_TESTED.
- Instrumented offline preflight: **2026-11-06T11:25:14.597838Z–2026-11-06T11:25:14.957972Z** (21:55:14 Australia/Adelaide). Earlier source retrieval and exploratory availability checks preceded that interval; exact acquisition timestamps were not captured.
- Runtime: CPython **3.12.14**, Linux **6.18.57**, x86_64, glibc **2.41**. Bash **5.2.37**, Git **2.52.0**, uv **0.13.5**, GNU coreutils sha256sum **9.7**. Available executable hashes and measured command timings are in ASTRA-001-EXECUTION.json.

## Expected versus observed

| Verification gate | Expected | Observed | Status |
|---|---|---|---|
| Exact source ref | Approved merge commit | Connector returned exact SHA; seven source blob identities matched | PASSED |
| Original input integrity | Both frozen SHA-256 values match | `sha256sum -c SHA256SUMS.txt`: both OK, exit 0 | PASSED |
| Offline catalogue contract | Eight candidates, selected five | Unmodified phase_a.py returned 8 / 5 and two verified source hashes, exit 0 | PASSED |
| Shell / Python availability | Executable environment | Bash and CPython executed successfully | PASSED |
| Pinned extractor executable | yt-dlp reports exactly 2026.03.17 | No executable on PATH; no active-interpreter module | FAILED |
| Extractor version and binary hash | Version and SHA-256 captured | No binary to inspect | NOT_TESTED |
| YouTube network access | Bounded extractor request | No request sent; no speculative connectivity probe | NOT_TESTED |
| Phase B runner execution | Authorised single-video invocation after preflight | Runner read but not executed after stop condition | NOT_TESTED |
| Real metadata and video identity | JSON received and ID matched | No extractor output | NOT_TESTED |
| Manual / automatic language keys | Enumerated from actual metadata | No metadata; keys unknown, not empty lists | NOT_TESTED |
| Unique English choice | Unique eligible track under runner policy | Selector not applied to live data | NOT_TESTED |
| Subtitle download | One eligible-track attempt | Zero attempts | NOT_TESTED |
| WebVTT bytes, hash and structure | Real file, valid cues and text | No file created by this attempt; no bytes to validate | NOT_TESTED |

Frozen input hashes:

```text
70cc6b9846dad47c2092820794187e68b68ac5cba8056b97810fe209e4c53abc  INPUT/LOCAL-VERIFY-004_youtube_inventory.json
1785b6804b41cd2326a9e7050224337d5abf1c6aff10f29e00f4288985e0aadb  INPUT/LOCAL-VERIFY-004_selection_report.md
```

Source copies remained byte-identical after offline execution. No remote GitHub state or previous evidence was modified. The local source subset was kept read-only; Python bytecode writes were disabled.

## Browser versus extractor

The frozen target observation at **2026-11-06T10:15:22.182Z** records both a CC accessibility label of “Subtitles/closed captions unavailable” and a Settings/subtitle menu listing “English (auto-generated)”. The extractor supplied no observation in ASTRA-001 because it never ran. **Agreement, contradiction and caption availability remain NOT_TESTED.** Neither historical UI signal has been promoted into extraction evidence.

Source-language identity, transcript accuracy, caption completeness and audio correspondence remain **NOT_TESTED**.

## Runner inspection and limits

Static inspection confirms the expected version string `2026.03.17`, selected-five allowlist, required `--authorize-live` flag plus `LOCAL_VERIFY_004_ALLOW_NETWORK=YES`, separate `--authorize-subtitles` flag, and rejection under `CI=true` or `GITHUB_ACTIONS=true`. The active environment had neither CI flag set. Live authorisation flags/environment acknowledgement were not applied after the executable blocker.

The runner disables config, playlist traversal, cache and retry categories; sets a 10-second socket timeout and 60-second subprocess limits; uses `--skip-download`; and selects English using exact-before-regional, manual-within-tier precedence with ambiguity abstention. Its subtitle command invokes yt-dlp again with the watch URL. The two subprocess stages are not a literal two-HTTP-request limit; individual extractor requests are not counted by the runner. These are source-code observations, not execution results.

The existing WebVTT check is explicitly minimal. No structural or content verification was performed on a real subtitle here. A future witness must independently assess actual bytes and must not rely solely on a successful exit code or the runner's success label.

No account credentials, cookies, media downloads, playlists, retries, CAPTCHA bypasses, browser fallback, GitHub mutations or SOFA publications were used. No raw extractor output or signed URLs were generated, so there is no raw extraction payload to preserve or redact. The JSON embeds the measured offline command streams with their sizes and hashes.

## Recommendation

Continue this same one-video test in an authorised execution environment that already provides the exact pinned executable and permitted public YouTube network access. Record its binary hash and rerun preflight before applying the existing Phase B gates. Do not count ASTRA-001 as a live attempt, a no-captions result or evidence that YouTube blocked access. Provisioning/installing the missing executable was expressly outside this assignment and was not done.

ASTRA-001-SHA256SUMS.txt hashes the final JSON and this report. It excludes itself to avoid a self-referential checksum. The JSON additionally records this report's size/hash; its own size/hash are supplied by the checksum manifest.
