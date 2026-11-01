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

## Paid execution (not invoked by ChatGPT)

`gpt-6.1-sol` / Responses API / high reasoning / short-context Standard assumptions. Pricing reference: https://developers.openai.com/api/docs/models/gpt-6.1-sol — US$2 per 1M input tokens and US$10 per 1M output tokens. API usage and pricing can change. The runner applies conservative **estimated** US$3/M input and US$10/M output ledger calculations; tool calls are disabled, request size is capped and model outputs are never executed.

Create a dedicated OpenAI API project and personally configure project billing/spend enforcement of **US$20**. Avoid sharing API keys in chat or Git. The local ledger halts admission before a new request would exceed its **US$17 estimated stop**. It reserves cost before contacting the API; unknown usage retains the reservation. This is **not** a guaranteed hard account-wide cap; other processes, pricing changes, project enforcement delays, or requests outside this runner are beyond its control. One paid request per command only. Run only with a dedicated project key and manually reviewed, **redacted** evidence text. The basic secret filter is not exhaustive.

```sh
export OPENAI_API_KEY='...set securely in your shell, not in this document...'
python3 -m chaos_pilot paid-once \
  --case GITHUB-PRIVILEGED-PR \
  --reviewed-evidence /path/to/redacted-reviewed-summary.txt \
  --ack 'AUTHORIZE ONE PAID REQUEST'
```

The private report and local cost ledger are written under `.chaos-state/` (excluded from Git). Never commit them. SOFA contributes **zero** new public posts from this pilot until reviewed findings are independently approved for publication. Permission to read public SOFA examples is not permission to leak private findings there.

## Evidence and review

Output classes: `review_candidate_not_vulnerability` (offline heuristic); `private_review_pending` (model opinion); `confirmed`, `refuted`, `inconclusive`, `not_tested` reserved for human-reviewed, independently tested findings.

Require source SHA, file hash, observable behavior, expected behavior, mitigation, negative control, precise uncertainty, and an explicit reviewer decision before any vulnerability claim. No auto-merge or disclosure.

**The compiler is innocent. The security boundary must prove its own innocence.**