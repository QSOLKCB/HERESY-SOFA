# Evidence invariants

1. **No fabricated evidence.** A result exists only when an experiment actually ran and its receipt was generated.
2. **Claim status is explicit.** Use `executed`, `inferred`, `not_tested`, or `unsupported`; do not conflate them.
3. **Expected is not actual.** Hypotheses, expected outcomes, and actual observations are separate records.
4. **Reproduction is isolated.** Experiments use temporary directories and deterministic fixtures; random inputs are seeded.
5. **Receipts are machine-readable.** Record the experiment ID, UTC timestamp, runtime versions, command, exit code, observations, and SHA-256 hashes of evidence inputs.
6. **Private context stays private.** Receipts do not include usernames, hostnames, environment variables, or absolute paths.
7. **Platform limits are visible.** Never infer Windows behaviour from a Linux reproduction; label unavailable execution `not_tested`.
8. **Publication is opt-in.** Local evidence and drafts are not published contributions. No automated publishing, voting, or credentials.
9. **Mitigations are tested.** State limitations and only describe a mitigation as verified when the experiment exercises it.
10. **Humour is not a substitute for technical precision.** The explanation remains useful without its editorial voice.
