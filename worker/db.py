from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "worker" / "migrations"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    for migration in sorted(MIGRATIONS.glob("*.sql")):
        connection.executescript(migration.read_text(encoding="utf-8"))
    connection.commit()


def start_run(connection: sqlite3.Connection, run_type: str) -> int:
    cursor = connection.execute(
        "INSERT INTO ingestion_runs(run_type, started_at, status) VALUES (?, ?, ?)",
        (run_type, utc_now(), "running"),
    )
    connection.commit()
    return int(cursor.lastrowid)


def finish_run(connection: sqlite3.Connection, run_id: int, status: str, stats: dict, error: str | None = None) -> None:
    import json

    connection.execute(
        "UPDATE ingestion_runs SET finished_at = ?, status = ?, stats_json = ?, error_summary = ? WHERE id = ?",
        (utc_now(), status, json.dumps(stats, sort_keys=True), error, run_id),
    )
    connection.commit()
