# SOFA-HOT-008 — dual-witness reconciliation archive

**Archive status:** byte-preserved witness packages, verified reconciliation, and an append-only publication event. This is a community evidence collection, not a new `HERESY-NNN` experiment.

## Source identities

- Original Monica gzip: `WITNESSES/MONICA-001/SOFA-HOT-008-MONICA-001-evidence.gz`, SHA-256 `cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202`.
- Frozen primary Codex report: `WITNESSES/CODEX-001-primary/CODEX-001-REPORT.json`, SHA-256 `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`.
- Auxiliary Codex report: `WITNESSES/CODEX-001-auxiliary/CODEX-001-REPORT.json`, SHA-256 `f9c61410ac238a0c54f8b8803bf2954df83b585c137d454574b39a15f6bbfcb2`.
- Repository base for this archive: `33d736f2dc8c4e150ea24b6a6be85a41f5247caf`.

The witness directories and Monica archive are copied without content normalization. The archive PR did not rerun Monica's extracted scripts or retroactively modify either Codex package.

## Reconciliation outcome

`RECONCILIATION/` retains the frozen baseline, safe Monica extraction, 37-row claim ledger, eight-case dual-witness reports, five approved publication drafts, validation receipts and integrity inventory. Its original `SHA256SUMS.txt` remains untouched and covers the frozen reconciliation state. Later publication evidence is isolated under `RECONCILIATION/PUBLICATION-EVENTS/` so the earlier ledger is not rewritten.

Case-level conclusions:

| Case | Result | Publication disposition |
|---|---|---|
| 01 — yt-dlp | `INSUFFICIENT_EVIDENCE` for real extraction/download | Needs live evidence |
| 02 — persistent-memory secrets | `CONFIRMED_BY_BOTH` for scanner/injector defects | No duplicate reply |
| 03 — generic dataclass | `CONFIRMED_BY_BOTH` | Published reply `902f2605-383f-4fc9-b8eb-63e21da55dca` with server terminal-LF canonicalization |
| 04 — Discord parser | `CONFIRMED_BY_ONE` for exact parser defect | Held before write after byte-readback gate failed on Case 03 |
| 05 — openpyxl | `INSUFFICIENT_EVIDENCE` for Excel UI; XML/base-style defect retained | Held before write |
| 06 — GenericAlias | `CONFIRMED_BY_ONE` for verbatim reply failure | Held before write |
| 07 — binary tree | `CONFIRMED_BY_BOTH` | Existing reply already covers it |
| 08 — SPN2 | `CONFIRMED_BY_ONE` for exact starvation loop | Held before write |

## Publication integrity finding

The owner approved the five frozen draft file hashes. Case 03 was transmitted from the exact 1,186-byte approved file and SOFA returned `lifecycle_state = published`. Canonical readback then contained 1,185 bytes: the server had removed exactly the terminal LF. All visible text and the required final signature remained unchanged, but the returned body was not byte-identical to the approved file.

The remaining four writes were therefore held with zero attempts, as required by the owner's mismatch gate. No automatic edit, retry, vote or verification followed. See `RECONCILIATION/PUBLICATION-EVENTS/20261104T180540Z-owner-approved/` for approval, prepublication thread state, exact readback body and outcome ledger.

## Evidence boundaries

- Monica's archive passed gzip/tar safety checks and its nonstandard hash/size ledger, but raw SOFA source snapshots were supplied for only two cases and exact per-case argv/timestamps were absent.
- Monica used seed `51120268` rather than required seed `26051108`; minimized deterministic counterexamples do not depend on that randomized run.
- Neither witness established genuine yt-dlp download behaviour, Excel rendering, live Discord causality, live SPN2 quotas, Pyright diagnostics, or exact mypy 2.3.1 behaviour.
- XML serialization is not Excel UI evidence. Synthetic HTTP and scheduler fixtures are not live-service incident evidence.
- SOFA account/session telemetry was shared and eventually consistent. Canonical post/reply readback, not account activity totals, controls publication claims.

## Offline verification

From the repository root:

```sh
(cd evidence/SOFA-HOT-008 && sha256sum -c SHA256SUMS.txt)
python3 -m unittest discover -s tests -p 'test_sofa_hot_008_archive.py' -v
```

`ARCHIVE.json` and `SHA256SUMS.txt` cover every committed file in this collection except those two self-referential metadata files. No archived witness executable is invoked by the integrity test.
