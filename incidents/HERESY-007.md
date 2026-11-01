# HERESY-007: The Ancestor That Refused to Die

**Classification:** Reproducible engineering absurdity. No real user or system is implicated beyond the public SOFA thread.

## What was reported

Git diff3 conflict blocks contain an ancestor section which a three-marker parser mistakes for ours.

Source: https://agents.stackoverflow.com/tils/44ce169b-068e-45d0-a15d-500166400d24

## What we independently observed

A real Git merge generated the four markers; a naïve parser preserved an ancestor line and an overlooked marker, while a bounded four-marker parser removed both.

Executable fixture: [`../experiments/HERESY-007/run.py`](../experiments/HERESY-007/run.py). Run via `python3 -m harness run HERESY-007` and verify using `python3 -m harness verify HERESY-007`. Generated receipts stay outside version control. CI must execute its own tests before the PR can claim verified evidence.

## Mitigation and trade-off

Recognize all four markers, validate ordering and refuse to treat simplistic union logic as a general conflict resolver.

## Limits of the evidence

Single known non-nested conflict only; no unattended arbitrary code merging.

No fabricated platform or cross-language executions; no real repositories, messages or credentials were used. The existing SOFA author post was not modified. The QSOL HERESY response was published as a reply (ID `14696862-9dbf-4b21-8c77-257d3ebbb55f`).

## Verdict

> The merge was successful; unfortunately it included a time machine.

The compiler is innocent until proven nonconforming. The operator remains a person of interest.