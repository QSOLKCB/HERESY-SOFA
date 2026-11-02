# HERESY-012 — The Four Revocations in a Trench Coat

**Classification:** Executable JUnit test-inventory completeness counterexample.
**Upstream:** [QEC PR #623](https://github.com/QSOLKCB/QEC/pull/623), original verifier at head `5c1b1ee5c9b6b1a036313670008e642699f51f32`; corrected independent guard at head `7774309df908f3568cf7d4055f3c2ff1c4a3f4ae`.
**HERESY execution:** Independently constructed **synthetic** Python standard-library JUnit XML, not the upstream project's execution of QEC or Ed25519.

## Hypothesis

A CI evidence verifier that counts the number of testcases per function
family after stripping pytest's parameter suffix can accept eleven green
records while failing to establish coverage of all four required dimensions:
operation, signer, capability, and policy revocation.

## Reproduce

From the HERESY-SOFA repository root:

`python3 -m harness run HERESY-012`

Then validate the **locally generated** receipt and source hashes:

`python3 -m harness verify HERESY-012`

The harness uses a bounded, disposable subprocess running
`experiments/HERESY-012/run.py`. It generates self-contained
eleven-case XML inventories using `xml.etree.ElementTree`.
No network, external dependency, QEC package, live CI credential, platform
service or third-party code is executed.

## Expected versus actual

**Correct coverage requirement:** One passing test each for seven
non-parametrized scenario families, and **exactly one** each for
`operation-REVOKED_OPERATION`,
`signer-REVOKED_SIGNER`,
`capability-REVOKED_CAPABILITY`, and
`policy-REVOKED_POLICY`. Eleven total is necessary but insufficient.

**Flawed verifier:** Truncates each testcase name at the first
`[`, validates family membership, uniqueness of full names, pass state,
and counts per family. Four distinct instances labeled
`operation-REVOKED_OPERATION-0` through
`operation-REVOKED_OPERATION-3` satisfy those counts although the
signer/capability/policy cases are absent.

**Mitigation:** Compare exact expected pytest node names including parameter
identities and reason labels, and reject any absent, duplicated, substituted,
skipped, failed, errored or unrelated testcase. The control fixture containing
the actual expected four different dimensions must remain accepted.

The reproducer also checks incorrectly paired dimension/reason labels, missing
testcase, wrong module, and failed/errored/skipped controls. Execution returns
nonzero if any expected observation fails.

## Distinct evidence provenance

The original QEC issue was a [Codex P2 finding](https://github.com/QSOLKCB/QEC/pull/623)
against QEC's JUnit completeness-check logic. The later corrective QEC
[dedicated run 41356155761](https://github.com/QSOLKCB/QEC/actions/runs/41356155761)
reported 15 verifier tests passing, 11 signed live-socket adversarial cases
passing, and a verified 11-node inventory. Those are **QEC Actions results,
not HERESY-SOFA-local executions**.

This experiment independently tests the narrow logic flaw using only synthetic
testcase listings. It does not demonstrate that QEC actually omitted any of
the required revocation executions, forge real CI artifacts, or prove malicious
tampering of GitHub Actions. Any historical upstream status is referenced by
its exact source head rather than reinterpreted from later branches.

## Limitations and claims

- `executed` applies only to the Python synthetic XML reproducer
  **after** its run exits zero and its receipt verifies.
- `not_tested`: QEC cryptography, network, and hardware code in HERESY.
- `unsupported`: an assertion that QEC actually omitted the four
  dimensions, that real-world attackers manipulated artifacts, or that the
  example proves an external CI compromise.
- Generated receipts remain under `receipts/generated/` and are never
  committed or described as cross-platform immutable evidence.

[Read the incident dossier](../../incidents/HERESY-012.md) or the
[unpublished SOFA candidate](../../blueprints/HERESY-012/BLUEPRINT.md).
