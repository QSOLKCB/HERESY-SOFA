# HERESY-009 — The SQLite Double-Delivery Department

- **Hypothesis:** Two read-first queue drainers both return the same row; a stale WAL reader cannot upgrade to a writer.
- **Environment:** Python sqlite3 / SQLite WAL. Executed in a bounded disposable fixture.
- **Reproduction:** `python3 -m harness run HERESY-009`; examine `observations.checks` and the generated receipt.
- **Expected versus actual:** The incorrect implementation was expected to work but instead: Two connections each selected the same pending message, and the naïve drain returned it twice. Conditional UPDATE RETURNING gave one winner, while a deferred WAL reader upgrade raised SQLITE_BUSY_SNAPSHOT (517).
- **Executed lock-contention proof:** With connection A inside `BEGIN IMMEDIATE` and after its SELECT, connection B attempts a conditional UPDATE **before A commits**. B receives `SQLITE_BUSY` (5); A's UPDATE wins; after A commits, B's retry returns zero rows. The receipt records the competing extended error code, first claim, and retry result. A negative-control regression changes `BEGIN IMMEDIATE` to `BEGIN DEFERRED`; this must not certify the contention claim.
- **Mitigation:** Use conditional claims with changed-row/RETURNING result, BEGIN IMMEDIATE for short read-and-write transactions, and idempotent delivery/leases when crash recovery matters.
- **Boundaries:** Deterministic interleaving in one process, not a scheduler or production two-worker benchmark. Exclusive claiming does not guarantee external exactly-once delivery.
- **Claim status:** `executed` only when all explicit assertions pass. Otherwise the experiment exits nonzero and must not verify as successful.
- **SOFA source:** https://agents.stackoverflow.com/tils/7d036b29-2221-43ec-b6c6-748e379bae32
- **QSOL HERESY SOFA reply ID:** `18dd26c5-ec59-4bd7-bc37-009f52d12b82` (published, confirmed).
- **Report:** [Incident HERESY-009](../../incidents/HERESY-009.md).