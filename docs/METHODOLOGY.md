# Methodology

Each experiment declares a falsifiable hypothesis, a bounded environment, minimal steps, expected behaviour, actual observations, a mitigation, limitations, and provenance.

## Claim vocabulary

- `executed`: directly observed by a recorded command in the stated environment.
- `inferred`: a reasoned conclusion not directly established by that execution.
- `not_tested`: no execution was performed for the claim or platform.
- `unsupported`: the environment or available evidence cannot establish the claim.

The labels describe evidence, not confidence. A successful Linux byte-level test does not establish how Windows `cmd.exe` behaves.

## Execution and receipts

The harness launches one experiment at a time in a fresh temporary working directory. It records a normalized command, the process exit code, captured observations, runtime versions, timestamp, and hashes of the manifest and entrypoint. It does not record arbitrary environment variables, hostnames, or absolute paths. A nonzero experiment exit is preserved in the receipt and is a failed run.

`harness verify` checks the receipt's basic schema, the experiment identifier, and current evidence hashes. It does not re-run the experiment or certify that a claim is scientifically sound. Receipts under `receipts/generated/` are local outputs; do not check them in as canonical results.

## Reproducibility

Prefer fixed inputs, explicit seeds, standard-library-only mechanisms, temporary directories, and explicit process exit codes. Where behaviour is timing-, platform-, or implementation-dependent, record that limitation rather than presenting one execution as universal.
