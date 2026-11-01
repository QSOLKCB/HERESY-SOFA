import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


with tempfile.TemporaryDirectory(prefix="heresy-sqlite-") as directory:
    root = Path(directory)
    source = root / "source.sqlite"
    copied = root / "copied.sqlite"
    backed_up = root / "backup.sqlite"

    connection = sqlite3.connect(str(source))
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
    connection.commit()
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.execute("INSERT INTO records(value) VALUES (?)", ("committed-in-wal",))
    connection.commit()

    shutil.copyfile(str(source), str(copied))
    backup_connection = sqlite3.connect(str(backed_up))
    connection.backup(backup_connection)
    backup_connection.close()

    try:
        copied_rows = sqlite3.connect(str(copied)).execute(
            "SELECT value FROM records"
        ).fetchall()
        copied_read_error = None
    except sqlite3.Error as error:
        copied_rows = []
        copied_read_error = str(error)
    copied_check = sqlite3.connect(str(copied)).execute("PRAGMA integrity_check").fetchone()[0]
    backup_connection = sqlite3.connect(str(backed_up))
    backup_rows = backup_connection.execute("SELECT value FROM records").fetchall()
    backup_check = backup_connection.execute("PRAGMA integrity_check").fetchone()[0]
    backup_connection.close()
    connection.close()

    print(
        json.dumps(
            {
                "claims": {
                    "main_file_copy_may_omit_committed_wal_data": "executed",
                    "copied_database_integrity_check_can_be_ok": "executed",
                    "sqlite_backup_api_preserves_committed_row": "executed",
                },
                "observations": {
                    "journal_mode": "WAL",
                    "copied_rows": copied_rows,
                    "copied_read_error": copied_read_error,
                    "copied_integrity_check": copied_check,
                    "backup_rows": backup_rows,
                    "backup_integrity_check": backup_check,
                },
                "mitigation": "Use sqlite3.Connection.backup() or another SQLite-consistent backup mechanism.",
            },
            sort_keys=True,
        )
    )
