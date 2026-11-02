# Verify the identities of parametrized CI tests, not merely their count

**Status:** Unpublished SOFA Blueprint candidate — HERESY-012.
**Subject:** Test-completeness evidence and falsifiable CI receipts.

## Problem

Suppose an adversarial trial must exercise *exactly one* case for each of
four revocation dimensions: operation, signer, capability and policy.
Pytest produces separate parameterized node IDs, such as:

`test_revoke[operation-REVOKED_OPERATION]`
`test_revoke[signer-REVOKED_SIGNER]`
`test_revoke[capability-REVOKED_CAPABILITY]`
`test_revoke[policy-REVOKED_POLICY]`

A CI checker may accept a JUnit document if it contains four distinct
instances of the test family and eleven total passing tests. But if it
computes the family with `name.split("[", 1)[0]`, it discards
the very identities that establish coverage. Four differently named
`operation-REVOKED_OPERATION-N` cases can satisfy the count.

This is a **proof-completeness bookkeeping flaw**, not a demonstrated
bypass of the runtime authorization boundary.

## Narrow design contract

1. Predeclare the full expected node ID set independently of test results.
2. Parse JUnit and require the exact expected module, unique complete name,
   no skipped/error/failure children, and the full set equality.
3. Refuse *any* missing, extra or substituted parameter identity, even if
   family counts, totals and a success exit code look correct.
4. Save exact-source CI JUnit and the verifier result as distinct per-run
   evidence. A checksum proves only content consistency, not external
   custody or that a reported test truly ran.
5. Test the verifier with synthetic negative controls, including a substituted
   all-operation inventory and incorrectly paired dimensions/reasons.

Minimal Python-like pseudocode:

```python
required = {
    "test_revoke[operation-REVOKED_OPERATION]",
    "test_revoke[signer-REVOKED_SIGNER]",
    "test_revoke[capability-REVOKED_CAPABILITY]",
    "test_revoke[policy-REVOKED_POLICY]",
}
seen = set()
for case in junit_testcases:
    name = case.attrib["name"]
    if name not in required or name in seen or any(
        case.find(tag) is not None for tag in ("failure", "error", "skipped")
    ):
        raise ValueError("incomplete revocation coverage")
    seen.add(name)
if seen != required:
    raise ValueError("missing revocation dimension")
```

## Local reproducibility and provenance

HERESY-SOFA's independent, standard-library fixture:

`python3 -m harness run HERESY-012`
`python3 -m harness verify HERESY-012`

The old and corrected checker behaviours are both exercised against
**synthetic** eleven-test XML inventories. The source finding is QEC
[PR #623](https://github.com/QSOLKCB/QEC/pull/623); its original head
was `5c1b1ee5c9b6b1a036313670008e642699f51f32`
and the corrected head was
`7774309df908f3568cf7d4055f3c2ff1c4a3f4ae`.
QEC's corrected [CI run 41356155761](https://github.com/QSOLKCB/QEC/actions/runs/41356155761)
is **external evidence** and not executed by this fixture.

## Limitations

No proof that QEC actually skipped a revocation case; no external
production data, signed keys, genuine network revocation or actual attacker
involved. The fixture models one known failure mode and does not validate
arbitrary JUnit schemas, runner identity or CI platform integrity.
It uses no automation to post to SOFA and makes no publication claim.

**Publication status: unpublished.**
