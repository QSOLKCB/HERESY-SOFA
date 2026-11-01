# Evidence review checklist (Stage 2)

Use this before accepting a new experiment, mitigation or SOFA-facing draft. Review **the exact commit SHA** and write down which steps were executed rather than inferred.

## Reproduction

- [ ] State a falsifiable claim with expected **and** actual behaviour.
- [ ] Use bounded, disposable fixtures; never operate against production data or credentials.
- [ ] Include the complete reproduction command and the interpreter/runtime versions.
- [ ] Verify the experiment's observed output and every required child exit code before assigning `executed`.
- [ ] Negative-control test: replace or disable a required child command; ensure a nonzero exit and a failed receipt instead of success paperwork.
- [ ] Distinguish `executed`, `inferred`, `not_tested`, `unsupported`, including platform-specific claims.

## Mitigation

- [ ] Test failing and working cases with the same fixture, and state expected-versus-observed outputs.
- [ ] Test boundary values and nested data where relevant; watch for silent coercion, partial writes, and false-success exit codes.
- [ ] Preserve the original counterexample as a regression fixture.
- [ ] Document assumptions, platform limitations, and any new risk introduced by the mitigation.

## Provenance

- [ ] Run `python3 -m unittest discover -s tests -v` and any relevant blueprint test suite.
- [ ] Generate local receipts, then verify hashes using `python3 -m harness verify-all`.
- [ ] Do not commit generated receipts as if they were immutable cross-platform observations.
- [ ] Confirm no personal details, external-service secrets, or host-specific absolute paths entered public evidence.
- [ ] Check cited upstream sources/standards separately from experimental observations.
- [ ] Keep SOFA status explicit: **candidate is not published**; publication requires human review and explicit approval.

## Interpretation

A passing receipt proves that the current file hashes and basic receipt schema match an observed local run; it does not establish correctness on all runtimes or a complete application security boundary. Independent deployment review remains separate from an independently written integration test.

**Failure to execute is a failed test, not an absence of objections from the Compiler Inquisitor.**