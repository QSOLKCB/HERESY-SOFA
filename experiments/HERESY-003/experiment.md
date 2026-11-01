# HERESY-003 — Schrödinger's SQLite Backup

- **Hypothesis:** Copying only the main database file while a committed transaction remains in a WAL can omit that transaction even though the copied database passes `PRAGMA integrity_check`.
- **Environment:** Python 3 `sqlite3` and SQLite; WAL enabled with automatic checkpointing disabled.
- **Minimal reproduction:** Create and commit a table before enabling WAL, commit a row in WAL, copy the main file while the connection remains open, then inspect the copy.
- **Expected behaviour:** The raw file copy can omit the committed row; a structural integrity check may still return `ok`. `Connection.backup()` should include the committed row.
- **Actual observations:** The output records copied rows or a read error, the copied database integrity check, rows in the API backup, and its integrity check.
- **Mitigation:** Use SQLite's backup API or another SQLite-aware backup method rather than copying the live main file alone.
- **Limitations:** WAL and checkpoint behaviour depend on SQLite state and version. The experiment demonstrates this controlled case, not every backup strategy or concurrent workload.
- **Evidence provenance:** The fixture creates databases only under a temporary directory, uses a fixed row value, and closes connections after both backup observations.
