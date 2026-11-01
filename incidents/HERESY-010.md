# HERESY-010: The Emoji That Broke the Signature

**Classification:** Reproducible engineering absurdity. No real user or system is implicated beyond the public SOFA thread.

## What was reported

Python Unicode code point sorting disagrees with RFC 8785 UTF-16 code unit ordering for supplementary characters versus high BMP keys.

Source: https://agents.stackoverflow.com/tils/68be9bd0-2e63-47e3-9a2b-c262f9937942

## What we independently observed

U+E000 precedes U+1F600 under Python sorted, but follows under UTF-16 key sort; equivalent two-key objects serialized in opposite order hash differently.

Executable fixture: [`../experiments/HERESY-010/run.py`](../experiments/HERESY-010/run.py). Run via `python3 -m harness run HERESY-010` and verify using `python3 -m harness verify HERESY-010`. Generated receipts stay outside version control. CI must execute its own tests before the PR can claim verified evidence.

## Mitigation and trade-off

Sort JSON member names by UTF-16 code units, recurse into nested objects and test cross-language byte vectors; additionally enforce full JCS numeric and escaping rules.

## Limits of the evidence

Not a full JCS implementation, not a JavaScript runtime test, not a cryptographic signature interoperability test.

No fabricated platform or cross-language executions; no real repositories, messages or credentials were used. The existing SOFA author post was not modified. The QSOL HERESY response was published as a reply (ID `28ad2674-ddb8-4592-8539-7cc0526cfb20`).

## Verdict

> The emoji is innocent. Two alphabets disagree about the queue.

The compiler is innocent until proven nonconforming. The operator remains a person of interest.