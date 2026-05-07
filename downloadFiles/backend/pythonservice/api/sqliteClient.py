from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).resolve().with_name("database.db")
_local = threading.local()


SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    job_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL NOT NULL DEFAULT 0,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    worker_id TEXT,
    source_id TEXT,
    title TEXT,
    thumbnail TEXT,
    filename TEXT,
    filepath TEXT,
    size INTEGER,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_downloads_queue
    ON downloads (status, next_attempt_at, created_at);

CREATE INDEX IF NOT EXISTS idx_downloads_user_history
    ON downloads (user_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _open_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, isolation_level=None, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def get_db() -> sqlite3.Connection:
    connection = getattr(_local, "connection", None)
    if connection is None:
        connection = _open_connection()
        _local.connection = connection
    return connection


def create_table(conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    db = conn or get_db()
    db.executescript(SCHEMA)
    return db


def get_setting(key: str, default: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Optional[str]:
    db = conn or get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return row["value"]


def set_setting(key: str, value: Optional[str], conn: Optional[sqlite3.Connection] = None) -> None:
    db = conn or get_db()
    db.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )


def clear_settings(conn: Optional[sqlite3.Connection] = None) -> None:
    db = conn or get_db()
    db.execute("DELETE FROM settings")


def recover_incomplete_downloads(conn: Optional[sqlite3.Connection] = None) -> None:
    db = conn or get_db()
    db.execute(
        """
        UPDATE downloads
        SET
            status = CASE
                WHEN cancel_requested = 1 THEN 'cancelled'
                ELSE 'queued'
            END,
            progress = CASE
                WHEN cancel_requested = 1 THEN progress
                ELSE 0
            END,
            worker_id = NULL,
            next_attempt_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE status IN ('downloading', 'processing')
        """
    )
