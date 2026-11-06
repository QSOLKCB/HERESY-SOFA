# LOCAL-VERIFY-004 — owner-channel reconnaissance (Phase A)

**Status:** PHASE_A_OFFLINE_VALIDATED. Actual yt-dlp metadata extraction and subtitle downloads are **NOT_TESTED**. No experiment success, network observation, YouTube caption download, or SOFA publication is claimed.

## Immutable primary inputs

The two supplied Astra Cloud Browser artifacts are preserved byte-for-byte under INPUT/. SHA256SUMS.txt identifies their original uploaded bytes; RUNNER/phase_a.py verifies hashes, the eight-video catalogue, selected-five contract, provisional negative, URL identity and observation provenance. Astra inspected eight videos from @trentslade83 on 2026-11-06: seven browser-menu English auto-caption listings and one provisional UI negative. These are browser observations, NOT extractor results. All seven menu positives had conflicting CC-button accessibility labels. No manual or native multilingual captions were verified.

From the repository root:

    python3 evidence/LOCAL-VERIFY-004/RUNNER/phase_a.py
    python3 -m unittest discover -s tests -p 'test_local_verify_004.py' -v
    (cd evidence/LOCAL-VERIFY-004 && sha256sum -c SHA256SUMS.txt)

## Phase B — prepared, NOT EXECUTED

RUNNER/phase_b.py is a separate manual-only executable. Never add it to CI, run-all, a scheduled task, or automated publishing. The default invocation refuses network access. It requires all of:

- A video ID from the exact frozen five.
- Explicit --authorize-live CLI flag.
- Local environment acknowledgement LOCAL_VERIFY_004_ALLOW_NETWORK=YES.
- An executable reporting exactly yt-dlp 2026.03.17.
- A separate --authorize-subtitles flag to request subtitles after metadata extraction.

CI=true or GITHUB_ACTIONS=true blocks execution. No cookies, authentication, saved browser profile, bypasses, bulk crawling, audio/video downloads, or automatic retries. Restrict to one video per run and bounded subprocess timeouts.

Example for a **future separately approved execution only** (this PR does not approve live execution):

    LOCAL_VERIFY_004_ALLOW_NETWORK=YES python3 evidence/LOCAL-VERIFY-004/RUNNER/phase_b.py --video-id dKp50fVKUtw --authorize-live --authorize-subtitles

The runner obtains --dump-single-json metadata while skipping video download, selects a uniquely identifiable English WebVTT track (exact-before-base, manual-within-tier), then optionally requests that caption track with --skip-download. It preserves mismatches with the provisional negative and checks WebVTT header, cue timing, size and SHA-256. Structural verification does not establish caption accuracy, completeness, correctness of language or audio correspondence.

Outputs are private temporary files **outside the repository**, with a 0700 directory and raw output/receipt files mode 0600. Raw extractor metadata may contain expiring signed retrieval URLs: never commit or publish the raw directory. Preserve exact execution results privately; create a separately reviewed, sanitised public evidence package. Successful metadata extraction does not prove actual subtitle download.

## Outstanding evidence

Phase A cannot establish real YouTube extraction semantics, whether -orig means source language, caption download success, or permanent absence of CorpoWars OST captions. Changed UI/extractor state needs investigation, not premature classification as a YouTube bug. A live campaign requires explicit owner approval of the five exact source URLs and an external request budget. No SOFA write, vote or verification is performed by either runner.
