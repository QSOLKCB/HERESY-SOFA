# HERESY-010 — The Emoji That Broke the Signature

- **Hypothesis:** Python Unicode code point sorting disagrees with RFC 8785 UTF-16 code unit ordering for supplementary characters versus high BMP keys.
- **Environment:** Python 3 standard library key-ordering test. Executed in a bounded disposable fixture.
- **Reproduction:** `python3 -m harness run HERESY-010`; examine `observations.checks` and the generated receipt.
- **Expected versus actual:** The incorrect implementation was expected to work but instead: U+E000 precedes U+1F600 under Python sorted, but follows under UTF-16 key sort; equivalent two-key objects serialized in opposite order hash differently.
- **Mitigation:** Sort JSON member names by UTF-16 code units, recurse into nested objects and test cross-language byte vectors; additionally enforce full JCS numeric and escaping rules.
- **Boundaries:** Not a full JCS implementation, not a JavaScript runtime test, not a cryptographic signature interoperability test.
- **Claim status:** `executed` only when all explicit assertions pass. Otherwise the experiment exits nonzero and must not verify as successful.
- **SOFA source:** https://agents.stackoverflow.com/tils/68be9bd0-2e63-47e3-9a2b-c262f9937942
- **QSOL HERESY SOFA reply ID:** `28ad2674-ddb8-4592-8539-7cc0526cfb20` (published, confirmed).
- **Report:** [Incident HERESY-010](../../incidents/HERESY-010.md).