"""SQLite queued message: reproduce stale SELECT duplication and snapshot upgrade.

Only uses a disposable SQLite DB in tempfile.TemporaryDirectory().
"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

CLAIMS = ("two_readers_can_duplicate_delivery", "conditional_update_only_one_wins",
          "deferred_reader_upgrade_hits_busy_snapshot", "immediate_claim_handles_contention")

def report(checks, detail):
    ok = bool(checks) and all(checks.values())
    print(json.dumps({"claims":{k:"executed" if ok else "not_tested" for k in CLAIMS},
        "observations":{"all_checks_passed":ok,"checks":checks,"details":detail,
                        "sqlite_version":sqlite3.sqlite_version,"platform":"local temporary SQLite WAL"},
        "mitigation":"Claim with conditional UPDATE ... RETURNING (or check rowcount) within BEGIN IMMEDIATE; deliver only rows won. Document at-most-once versus crash-safe lease semantics."},sort_keys=True))
    return 0 if ok else 1

def connect(path):
    c=sqlite3.connect(path,timeout=0.5,isolation_level=None)
    c.execute("PRAGMA busy_timeout=500")
    return c

def main():
    with tempfile.TemporaryDirectory(prefix="heresy-queue-") as tmp:
        path=str(Path(tmp)/"queue.sqlite")
        a=connect(path); b=connect(path)
        try:
            assert a.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower()=="wal"
            a.execute("CREATE TABLE message (id INTEGER PRIMARY KEY,status TEXT NOT NULL, body TEXT NOT NULL)")
            a.execute("INSERT INTO message VALUES (1,'pending','deliver me')")
            # Two drains inspect pending work before either mutates it.
            pending_a=a.execute("SELECT id,body FROM message WHERE status='pending'").fetchall()
            pending_b=b.execute("SELECT id,body FROM message WHERE status='pending'").fetchall()
            a.execute("UPDATE message SET status='delivered' WHERE id=1")
            b.execute("UPDATE message SET status='delivered' WHERE id=1")
            naïve_deliveries=pending_a+pending_b
            # Reset then make the UPDATE the actual ownership decision.
            a.execute("UPDATE message SET status='pending' WHERE id=1")
            win_a=a.execute("UPDATE message SET status='delivered' WHERE id=1 AND status='pending' RETURNING id").fetchall()
            win_b=b.execute("UPDATE message SET status='delivered' WHERE id=1 AND status='pending' RETURNING id").fetchall()
            # Independent WAL snapshot hazard: one transaction reads then another commits.
            a.execute("BEGIN DEFERRED")
            a.execute("SELECT COUNT(*) FROM message").fetchone()
            b.execute("INSERT INTO message VALUES (2,'pending','new arrival')")
            snapshot_code=None
            try:
                a.execute("UPDATE message SET status='delivered' WHERE id=2")
            except sqlite3.OperationalError as e:
                snapshot_code=getattr(e,"sqlite_errorcode",None)
            finally:
                a.execute("ROLLBACK")
            # IMMEDIATE serializes the claim before SELECT and observes latest row.
            a.execute("BEGIN IMMEDIATE")
            immediate_rows=a.execute("UPDATE message SET status='delivered' WHERE id=2 AND status='pending' RETURNING id").fetchall()
            a.execute("COMMIT")
            other_rows=b.execute("UPDATE message SET status='delivered' WHERE id=2 AND status='pending' RETURNING id").fetchall()
            checks={"two_readers_can_duplicate_delivery":len(naïve_deliveries)==2 and pending_a==pending_b,
                    "conditional_update_only_one_wins":win_a==[(1,)] and win_b==[],
                    "deferred_reader_upgrade_hits_busy_snapshot":snapshot_code==sqlite3.SQLITE_BUSY_SNAPSHOT,
                    "immediate_claim_handles_contention":immediate_rows==[(2,)] and other_rows==[]}
            return report(checks,{"naive_delivery_count":len(naïve_deliveries),
                "conditional_winners":[len(win_a),len(win_b)],"snapshot_extended_code":snapshot_code,
                "immediate_winners":[len(immediate_rows),len(other_rows)]})
        finally:
            a.close();b.close()

if __name__=="__main__":
    try:sys.exit(main())
    except (sqlite3.Error,AssertionError) as exc:
        print("HERESY-009: {}".format(type(exc).__name__),file=sys.stderr)
        sys.exit(1)