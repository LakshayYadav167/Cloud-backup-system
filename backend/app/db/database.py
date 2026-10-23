"""Database connection and initial schema definition for SQLite.

Zero-cost, embedded relational storage using Python's built-in sqlite3.
"""

from pathlib import Path
from typing import Generator
import sqlite3

from app.core.config import settings

# Initial SQL Schema for Phase 2 activation
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    mime_type TEXT DEFAULT 'application/octet-stream',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backups (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
    snapshot_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_files INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    checksum TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS backup_items (
    backup_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    file_snapshot_hash TEXT NOT NULL,
    PRIMARY KEY (backup_id, file_id),
    FOREIGN KEY (backup_id) REFERENCES backups (id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_created_at ON files (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backups_timestamp ON backups (snapshot_timestamp DESC);
"""


def get_db_path() -> Path:
    """Resolve and ensure the parent directory for the SQLite database."""
    # If DATABASE_URL is in format sqlite:///path, extract path
    raw_url = settings.DATABASE_URL
    if raw_url.startswith("sqlite:///"):
        relative_path = raw_url.replace("sqlite:///", "")
    else:
        relative_path = "./data/cloud_backup.db"

    db_path = Path(relative_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_db_connection() -> sqlite3.Connection:
    """Create a configured SQLite connection with row factories and WAL mode."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for concurrency and foreign key enforcement
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize database tables idempotently."""
    conn = get_db_connection()
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for yielding database connections."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
