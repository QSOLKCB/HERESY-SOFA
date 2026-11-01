# HERESY-012 — The Four Revocations in a Trench Coat

**Offence alleged:** Passing the headcount while losing three witnesses.

## Complaint

The [QEC #623](https://github.com/QSOLKCB/QEC/pull/623) adversarial
trial included four distinct revocation checks. The independent evidence
gate originally counted four entries from the parameterized test family,
but ignored the dimension/reason suffix when evaluating completeness.

Codex identified that four **uniquely named operation-only cases** could
stand in for the expected operation, signer, capability and policy tests.
That was a defect in evidence **accounting**, not evidence that the upstream
security trials were actually missing.

## Reproduction exhibit

The local standard-library experiment builds synthetic JUnit XML with
eleven passing cases. It compares a model of the original family-count
logic with a strict node-ID set verifier.

- **Control:** seven single cases plus the four real dimension/reason
  identities. Both verifiers accept this inventory.
- **Counterexample:** seven singles plus four different
  `operation-REVOKED_OPERATION-N` cases. The flawed checker
  approves the numbers; the strict checker rejects the missing identities.
- **Mitigation controls:** wrong dimension/reason pairing and rejected or
  missing testcases fail; valid complete inventories still pass.

Run `python3 -m harness run HERESY-012` and
`python3 -m harness verify HERESY-012`. Inspect
`observations.checks` in the generated receipt.

## What the judge actually ruled

The separate corrected QEC run
[41356155761](https://github.com/QSOLKCB/QEC/actions/runs/41356155761)
reported 15 verifier regression tests passed and all 11 live IRC socket
attack cases passed. That is upstream CI evidence; the standalone HERESY
fixture does **not** execute QEC's own tests, signed grants or network stack.

There is no basis here for a claim that three upstream cases did not run.
The vulnerability was the **independent completeness guard's inability to
recognize the substitution**.

## Sentence

Count the witnesses **and check their identities**. For every required
parameter dimension, predeclare its exact expected node ID; compare the
full observed set; fail closed on substitution and retain the JUnit source.

SOFA publication state: **unpublished candidate**, no automated post.
The compiler remains innocent. The paperwork inspector has been reassigned.
