# ASTRA-001 — LOCAL-VERIFY-004 preflight witness archive

**Disposition: `PREFLIGHT_FAILED`** (required `yt-dlp 2026.03.17` executable unavailable). **Live metadata extraction, subtitle download, WebVTT validation and browser/extractor reconciliation: `NOT_TESTED`.**

This append-only collection preserves the three original user-uploaded Astra witness artifacts *byte-for-byte*:

- `ASTRA-001-EXECUTION.json` — measured preflight, version/tool availability and exact Git source subset identity;
- `ASTRA-001-REVIEW.md` — human-readable interpretation and bounded limitations;
- `ASTRA-001-SHA256SUMS.txt` — exact file checksums of the two reports, excluding the manifest itself.

`tests/test_astra_001_archive.py` independently pins the full manifest bytes, its SHA-256, the two artifact hashes and sizes, and the fact that no extractor or subtitle attempt occurred. This validator is outside the source archive and never rewrites it. Run from the repository root:

```sh
(cd evidence/LOCAL-VERIFY-004/ASTRA-001 && sha256sum -c ASTRA-001-SHA256SUMS.txt)
python3 -m unittest discover -s tests -p 'test_astra_001_archive.py' -v
```

The observations are from Astra's separate environment; the offline preflight established `yt-dlp` was not available there. No YouTube request was made and no result about caption presence/absence follows. The source subset is pinned to merged PR #22 commit `783608c3449689c0c61b7ab4be9c07ce1f1b61d8`; this is not evidence of a complete local clone, a live extractor result, or a successful subtitle download.

**Do not treat this archive as Phase B success or run any network experiment in CI.** A future authorised native witness must use separate append-only receipts. Earlier LOCAL-VERIFY evidence, runner code and SOFA publications are outside this PR.
