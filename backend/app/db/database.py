"""Database connection and relational schema definition for SQLite.

Zero-cost, embedded relational storage using Python's built-in sqlite3.
Supports versioned files, immutable backup snapshots, and transactional safety.
"""

from pathlib import Path
from typing import Generator, Optional
import sqlite3

from app.core.config import settings

# Database Schema: files, file_versions, backups, and backup_items
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT DEFAULT 'application/octet-stream',
    current_version_id TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_versions (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    object_key TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    content_type TEXT NOT NULL,
    change_summary TEXT DEFAULT 'Initial upload',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
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
    version_id TEXT NOT NULL,
    file_snapshot_hash TEXT NOT NULL,
    PRIMARY KEY (backup_id, file_id),
    FOREIGN KEY (backup_id) REFERENCES backups (id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES file_versions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_filename ON files (filename);
CREATE INDEX IF NOT EXISTS idx_files_updated_at ON files (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_versions_file_id ON file_versions (file_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_file_versions_object_key ON file_versions (object_key);
CREATE INDEX IF NOT EXISTS idx_backups_timestamp ON backups (snapshot_timestamp DESC);
"""


def get_db_path(custom_url: Optional[str] = None) -> Path:
    """Resolve and ensure the parent directory for the SQLite database."""
    raw_url = custom_url or settings.DATABASE_URL
    if raw_url.startswith("sqlite:///"):
        relative_path = raw_url.replace("sqlite:///", "")
    else:
        relative_path = raw_url

    db_path = Path(relative_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_db_connection(custom_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a configured SQLite connection with row factories and foreign keys enabled."""
    if custom_path:
        conn = sqlite3.connect(custom_path, check_same_thread=False)
    else:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path), check_same_thread=False)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Try enabling WAL mode for disk files
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass

    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> None:
    """Initialize database tables and indexes idempotently."""
    if conn is not None:
        with conn:
            conn.executescript(SCHEMA_SQL)
    else:
        connection = get_db_connection()
        try:
            with connection:
                connection.executescript(SCHEMA_SQL)
        finally:
            connection.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for yielding database connections."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
