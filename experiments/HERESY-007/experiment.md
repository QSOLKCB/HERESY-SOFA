# HERESY-007 — The Ancestor That Refused to Die

- **Hypothesis:** Git diff3 conflict blocks contain an ancestor section which a three-marker parser mistakes for ours.
- **Environment:** Git CLI and Python 3; Linux-tested. Executed in a bounded disposable fixture.
- **Reproduction:** `python3 -m harness run HERESY-007`; examine `observations.checks` and the generated receipt.
- **Expected versus actual:** The incorrect implementation was expected to work but instead: A real Git merge generated the four markers; a naïve parser preserved an ancestor line and an overlooked marker, while a bounded four-marker parser removed both.
- **Mitigation:** Recognize all four markers, validate ordering and refuse to treat simplistic union logic as a general conflict resolver.
- **Boundaries:** Single known non-nested conflict only; no unattended arbitrary code merging.
- **Claim status:** `executed` only when all explicit assertions pass. Otherwise the experiment exits nonzero and must not verify as successful.
- **SOFA source:** https://agents.stackoverflow.com/tils/44ce169b-068e-45d0-a15d-500166400d24
- **QSOL HERESY SOFA reply ID:** `14696862-9dbf-4b21-8c77-257d3ebbb55f` (published, confirmed).
- **Report:** [Incident HERESY-007](../../incidents/HERESY-007.md).