# SOFA-HOT-008 — terminal-LF publication addendum

**Archive status:** four additional owner-authorized replies published and read back under the explicitly permitted one-final-LF canonicalization rule. This addendum is separate from the frozen SOFA-HOT-008 archive in PR #16 and does not change that commit.

## Publication results

| Case | Parent post | Published reply | Canonical body |
|---|---|---|---|
| 04 — Discord parser | `3eefb05a-c521-4cb7-8a4d-dbf709bf3101` | `5d942dc5-a57e-4671-804a-3a825afd3f80` | Approved 988-byte draft minus its final LF; 987 bytes |
| 05 — openpyxl | `47de513f-cd52-4b36-a43d-ec4cb89c972f` | `6f977ba0-b147-4798-a9fe-a7d73ee10bc3` | Approved 1,101-byte draft minus its final LF; 1,100 bytes |
| 06 — GenericAlias | `0b3591f6-75de-4661-a7a7-ec28193e1518` | `546d5c81-c410-4a3f-8520-1a504658ad2e` | Approved 1,119-byte draft minus its final LF; 1,118 bytes |
| 08 — SPN2 | `da4cf061-dba9-4c01-b42c-f94e6f3b6279` | `22e71c43-88e5-4598-8699-7ca07b8e3610` | Approved 1,265-byte draft minus its final LF; 1,264 bytes |

Every mutation returned `lifecycle_state = published`. Canonical thread and owned-post readback confirmed the reply ID, parent ID, QSOL HERESY agent identity, active state, actual body and required final signature. No retry, edit, vote, verification, deletion, merge or deployment occurred.

`SOURCE-EVENT/` is a byte-exact copy of the append-only custody event. Its per-case receipts preserve the canonical bodies and hashes; `PUBLICATION-EVENT.json` preserves mutation counts and evidence limitations; `SHA256SUMS.txt` covers every source-event file except itself.

The source event's `validate_event.py` retains paths relative to the custody tree where it originally ran. The repository-level `validate_addendum.py` maps those immutable receipt records to the already archived drafts under `evidence/SOFA-HOT-008/` and validates the same byte relationship without duplicating or changing them.

## Evidence boundaries

- Case 04 demonstrates a synthetic shell/parser failure, not live Discord causality.
- Case 05 establishes XML/base-style facts, not genuine Excel rendering.
- Case 06 retains single-witness CPython execution; Codex did not run Pyright.
- Case 08 is a deterministic fake-clock/fake-API simulation; live Internet Archive quotas and protocol semantics remain unverified.
- SOFA session activity counts are advisory. Canonical reply readback and the receipts control publication attribution.

## Frozen predecessor

- PR #16 head: `bb1eabd27a6606b6c229c32190942bcd9672a261`.
- Predecessor archive manifest SHA-256: `7386b1dd858330637b92c6bbdcef3bc3330dd4c100d2956ec942ba222f4174c7`.
- Monica gzip SHA-256: `cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202`.
- Primary Codex report SHA-256: `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`.

## Offline verification

From the repository root:

```sh
(cd evidence/SOFA-HOT-008-PUBLICATION-ADDENDUM-01 && sha256sum -c SHA256SUMS.txt)
python3 evidence/SOFA-HOT-008-PUBLICATION-ADDENDUM-01/validate_addendum.py
python3 -m unittest tests.test_sofa_hot_008_publication_addendum -v
```

No archived witness script, external service, credential, SOFA mutation or GitHub mutation is invoked by these checks.
