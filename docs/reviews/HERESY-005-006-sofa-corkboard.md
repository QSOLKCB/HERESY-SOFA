# HERESY-005/006 — SOFA publication and corkboard evidence audit

Review date: 2026-11-04. Original experiment PR: [#9](https://github.com/QSOLKCB/HERESY-SOFA/pull/9), merged to `main` as `9d41abcbb5b36bece471f3006015eac129573f9b`.

## What executed

| File | Source revision / result | Legitimate claim | Explicit exclusion |
| --- | --- | --- | --- |
| [HERESY-005-report.json](../../experiments/HERESY-005/HERESY-005-report.json) | `bb9042f9e8f626cf59bcac0113cf19dfbea801d7`; compile exit 0; native preflight exit 30; `NOT_RUN / UNCONFIRMED` | CUDA 12.4 compilation and device/driver preflight were executed and revealed no usable device | No control/fault CUDA assertion trial, no observed error 710, no poisoned-context test |
| [HERESY-006-report.json](../../experiments/HERESY-006/HERESY-006-report.json) | `1f4e568373764396aa6bd580d2e1cc30e0742c49`; `PASS / CONFIRMED` | 240 configurations with NetworkX 3.5 and CPython 3.14.4; 42 valid canonical cycle partitions; fixed-seed repeats stable | No observed hash-seed sensitivity; no upstream NetworkX API contract violation or universal stability conclusion |

Both report files include `evidence_tree_dirty=false` and hashes of *their own* execution-era source files. Later commits do not alter these historical receipts or imply the matrices were rerun.

## Correction verified separately

The parent verifier now independently checks the exact known fixture graph, partition identity/coverage, worker identity, and *a weighted modularity value calculated in the parent from the known edges*. This closes the case in which two mutually consistent worker-supplied modularity scores are wrong. Dependency-free tests inject the forgery and malformed record types; CI is required to pass. Earlier P1/P2 evidence-gate and redaction hardening from PR #9 is retained. The new oracle was **not** part of the previous matrix's execution source.

## Publication registry

- [HERESY-005 bounded preflight TIL](https://agents.stackoverflow.com/tils/dd9e3bfe-edeb-4596-8d59-26af83f26572): deliberately says assertion **NOT_RUN**.
- [HERESY-006 verification Blueprint](https://agents.stackoverflow.com/blueprints/4bcd561f-3968-4e61-a49b-abc636a05f79): distinguishes observed heuristic variation from a NetworkX defect and distinguishes historical matrix execution from the later verifier fix.

Published IDs were obtained from successful authenticated SOFA writes. The repo does not write to SOFA, store credentials or publish automatically.

## Static site policy

The visible `evidenceState` ("blocked" or "observed") is *not* the harness `status`. Both experiment manifests retain `placeholder` and `entrypoint: null`, preserving the dependency-free default `run-all` and excluding driver-dependent or optional NetworkX commands. The corkboard may display a published preflight TIL for a still-wanted assertion case; it must not equate "ON SOFA" with "CAUGHT".

GitHub Pages remains manual `workflow_dispatch`; no automatic deployment is part of this change.
