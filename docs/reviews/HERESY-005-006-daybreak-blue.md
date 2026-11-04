# HERESY-005/006 review outcome

Review target: PR #9 at `fb3ddc6b70e1d416dfc0c99cc906c52a0184f870`.

The requested dedicated Daybreak Blue feature was checked through Codex Security Cloud and was unavailable in this workspace (`securityReviewEnabled: false`). No generic security scan is represented as a Daybreak Blue review. An independent read-only Codex reviewer inspected the exact PR diff and reports against the requested Daybreak Blue scope.

## Findings and disposition

### P1 — enforce topology equivalence in the parent

The original parent trusted worker integrity booleans and did not reject a changed topology before classifying construction-order variation. Corrected: parent acceptance now recomputes the expected fixture topology fingerprint and rejects a mismatched result. A negative control mutates the topology hash and must fail.

### P1 — gate the fixed-seed claim and conclusion on observed controls

The original claim map labelled fixed-seed reproducibility `executed` unconditionally. Corrected: the classification is conditional on the observed boolean, and `CONFIRMED` now requires fixed-seed reproducibility, the separated-clique stability control, partition/modularity integrity, and actual seed/order divergence. Negative controls cover divergent fixed repeats and a failed stability control.

### P2 — independently validate worker provenance and result fields

The original parent did not independently validate all scenario, hash-seed, version, partition, count/size, topology, and modularity fields. Corrected: all are checked against the command configuration, parent runtime, deterministic fixture spec, and raw canonical partition. Negative controls cover omitted and duplicated nodes despite forged success booleans; a self-consistent alternate graph/partition/modularity tuple; wrong scenario, version, hash seed, topology and order; non-finite or inconsistent modularity; exit failure; malformed output; and timeout.

The hash-seed check is explicitly bounded: `PYTHONHASHSEED` is fixed at interpreter startup, so matching the parent-controlled environment and worker report verifies launch configuration but cannot independently prove internal causal use by Louvain.

## Areas with no findings

- CUDA safety: one block/thread and controlled assert; independent children; parent timeout; no reset, out-of-bounds access, stress, persistent kernel, or CUDA call after observing the synchronization result.
- CI and dependencies: both manifests remain placeholders; the default harness and driverless CI do not invoke either experiment; NetworkX remains confined to a disposable environment.
- Subprocess safety: argument arrays are used without a shell, and bounded timeouts fail closed.
- Leakage: no username, hostname, secret, `/home`, or `/tmp` value was found in either report.
- Evidence boundaries: HERESY-005 remains `NOT_RUN`/unconfirmed; HERESY-006 does not claim a NetworkX contract violation or universal behavior.

The correction is verified by the targeted negative controls and a regenerated real NetworkX 3.5 matrix. Report hashes bind the exact corrected evidence files; the final PR commit is recorded in the delivery summary.
