# Incident reports

Incidents are human-readable case files tied to executable experiments and fail-closed receipts. Humour is welcome; fabricated results are not.

| Case | Finding | Evidence |
|---|---|---|
| [HERESY-007](HERESY-007.md) | Diff3 merge resolver mistakenly retains the common ancestor | Disposable real Git merge, corrected four-marker parse |
| [HERESY-008](HERESY-008.md) | GIT_DIR used as Git's installation path, causing a wrong-repository index write | Disposable Git CLI simulation; Windows execution not tested |

| [HERESY-009](HERESY-009.md) | Read-first SQLite queue double-delivers; WAL upgrade gets BUSY_SNAPSHOT | Two SQLite connections, conditional claim and BEGIN IMMEDIATE |
| [HERESY-010](HERESY-010.md) | Python code-point key order differs from JCS UTF-16 order | UTF-16-order reference and divergent SHA-256 digests |

Generated receipts belong in `receipts/generated/`, not in version-controlled evidence claims.