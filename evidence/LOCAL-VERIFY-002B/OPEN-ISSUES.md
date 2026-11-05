# LOCAL-VERIFY-002B open issues

## Closed by this addendum

- Mypy 2.3.1: all 28 missing default/strict rows are `CHECKER_CONFIRMED`.
- Pyright 1.1.414: all 28 missing standard/strict rows are `CHECKER_CONFIRMED` using the official bundled CLI on Node 22.18.0.
- The prior LOCAL-VERIFY-002 mypy 1.19.1 evidence remains immutable and hash-valid.

## Still bounded or unverified

- No claim is made for mypy or Pyright versions other than the pinned versions.
- CPython runtime behavior was not rerun in 002B. Runtime comparisons cite immutable LOCAL-VERIFY-002 receipts.
- Checker acceptance after `# type: ignore` does not verify the runtime dataclass invariant.
- Pyright standard and strict deliberately differ on Unknown-related diagnostics; neither mode may be substituted for the other.
- `types.GenericAlias` runtime behavior does not imply static-call or specialization support.
- The tested literal ellipsis result concerns these user-defined generic fixtures; it is not a universal ban on ellipsis in every typing construct.
- No SOFA publication, vote or verification action occurred. Any publication remains a separate owner-reviewed phase.
