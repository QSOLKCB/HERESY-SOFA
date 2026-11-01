# QSOL CHAOS — The Security Inquisitor (pilot v0.1.0)

**Status:** pilot foundation. No autonomous model access, credential scanning, SOFA publishing, or production probing.

## Research question

Can documented failure classes from the [Codecov 2021 uploader compromise](https://about.codecov.io/apr-2021-post-mortem/), [GitHub's privileged pull-request workflow guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target) and [CircleCI's 2023 incident](https://circleci.com/blog/jan-4-2023-incident-report/) predict testable trust-boundary weaknesses or controls in **authorized, pinned, public QSOLKCB source code**?

A negative candidate result means *nothing was demonstrated under this test*, not "secure". A heuristic flag means *review needed*, not "vulnerable". Neither public incident reports nor SOFA posts grant authority to access production systems.

## Fixed pilot scope (snapshot SHAs read on 2026-11-01)

- `QSOLKCB/HERESY-SOFA` @ `4faf7bfb5b2ff6e27d95756ec3e081f75e3e7239`
- `QSOLKCB/PROVENANCE` @ `2db834540e2f585ceda3be7ff7e46286c15d8b6c`
- `QSOLKCB/QSOL-IBAE` @ `2f9c3e826ee177a75cf12ca0eeb7d5a97070cff9`

No private repositories, deployment hosts, credentials, connected services, API data or external systems are authorized by this pilot. All repository content and report text are *untrusted data*, never instructions for the runner.

## No-cost dry run

```sh
python3 -m chaos_pilot dry-run
python3 -m unittest discover -s tests -p 'test_chaos_pilot.py' -v
```

The `compare` subcommand operates on a user-supplied, read-only file copy representing a pinned repository path. It does not fetch content, run code or assert a vulnerability. Its `flags` are candidate heuristics and must be human-reviewed against actual YAML semantics and context.

```sh
python3 -m chaos_pilot compare \
  --repo QSOLKCB/HERESY-SOFA \
  --sha 4faf7bfb5b2ff6e27d95756ec3e081f75e3e7239 \
  --path .github/workflows/ci.yml --snapshot /path/to/checked/ci.yml
```

There is intentionally **no** automated vulnerability reproduction command in the API module. A future reproduction executor must launch only human-reviewed, synthetic fixtures in a verified network-disabled OS sandbox such as a hardened rootless container. A Python subprocess plus a helpful prompt is **not** an isolation boundary.

## Offline review planning (no cloud integration)

HERESY-SOFA's [agent policy](../AGENTS.md) forbids adding cloud services or
credentials. Therefore the CHAOS pilot contains **no live Responses API path**,
no account-key handling, no network request sender, and no paid model command.
Prior versions of this unmerged PR proposed a `paid-once` option; that option
was removed in response to the Codex P1 review.

The hypothetical `gpt-6.1-sol` template and budget calculator are local
planning artifacts, **not connected services**. `plan-review` consumes
operator-reviewed redacted notes, calculates a prospective request digest,
byte count and estimated reservation, and prints **metadata only**; it does
not transmit data, save the notes, reserve real funds or write any API report.
The independent ledger in `budget.py` is an offline budgeting simulation,
not an accounting record of actual API charges.

```sh
python3 -m chaos_pilot plan-review \
  --case GITHUB-PRIVILEGED-PR \
  --reviewed-evidence /path/to/redacted-reviewed-summary.txt
```

Any future paid API integration requires **a separately approved project or
explicit revision to this repository's policy**, independent credentials,
security review and a new scoped PR. The suggested $20 project ceiling and $17
local estimate are design targets only; no API budget is being consumed here.

## Byte-accurate evidence

The `compare` subcommand reads the supplied snapshot using `read_bytes()`,
hashes those bytes directly with SHA-256, and decodes UTF-8 strictly **only
for analysis**. CRLF, bare CR and LF remain distinct in the recorded digest.
Invalid UTF-8 and oversized snapshots fail closed. A receipt remains a
claim about the exact bytes **supplied by the operator**: it does not
independently re-fetch or verify those bytes against the named Git commit.

## Evidence and review

Output classes: `review_candidate_not_vulnerability` (offline heuristic); `private_review_pending` (model opinion); `confirmed`, `refuted`, `inconclusive`, `not_tested` reserved for human-reviewed, independently tested findings.

Require source SHA, file hash, observable behavior, expected behavior, mitigation, negative control, precise uncertainty, and an explicit reviewer decision before any vulnerability claim. No auto-merge or disclosure.

**The compiler is innocent. The security boundary must prove its own innocence.**