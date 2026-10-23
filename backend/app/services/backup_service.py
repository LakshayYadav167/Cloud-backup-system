"""Domain service managing point-in-time backup snapshots and audit logs."""

from typing import Optional
import hashlib
import sqlite3
import uuid

from app.models.schemas import BackupHistoryResponse, BackupSnapshotResponse


def format_bytes_readable(size_bytes: int) -> str:
    """Format byte integers into human-readable strings."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class BackupService:
    """Service layer managing backup snapshots and immutable historical records."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def trigger_backup(self, notes: Optional[str] = None) -> BackupSnapshotResponse:
        """Create an immutable snapshot of all currently active files and their versions."""
        backup_id = str(uuid.uuid4())
        cursor = self.db.cursor()

        cursor.execute(
            """
            SELECT f.id AS file_id, v.id AS version_id, v.sha256, v.size_bytes
            FROM files f
            JOIN file_versions v ON f.current_version_id = v.id
            WHERE f.is_deleted = 0
            ORDER BY f.id ASC
            """
        )
        active_items = cursor.fetchall()

        total_files = len(active_items)
        total_bytes = sum(item["size_bytes"] for item in active_items)

        # Compute aggregate snapshot checksum: SHA-256 of concatenated sorted hashes
        manifest_hasher = hashlib.sha256()
        for item in active_items:
            manifest_hasher.update(f"{item['file_id']}:{item['sha256']}\n".encode("utf-8"))
        snapshot_checksum = manifest_hasher.hexdigest()

        with self.db:
            self.db.execute(
                """
                INSERT INTO backups (id, status, total_files, total_bytes, checksum, notes)
                VALUES (?, 'COMPLETED', ?, ?, ?, ?)
                """,
                (
                    backup_id,
                    total_files,
                    total_bytes,
                    snapshot_checksum,
                    notes or f"Automated snapshot of {total_files} active files",
                ),
            )

            for item in active_items:
                self.db.execute(
                    """
                    INSERT INTO backup_items (backup_id, file_id, version_id, file_snapshot_hash)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        backup_id,
                        item["file_id"],
                        item["version_id"],
                        item["sha256"],
                    ),
                )

        cursor.execute(
            "SELECT snapshot_timestamp FROM backups WHERE id = ?",
            (backup_id,),
        )
        row = cursor.fetchone()

        return BackupSnapshotResponse(
            id=backup_id,
            status="COMPLETED",
            snapshot_timestamp=str(row["snapshot_timestamp"]),
            total_files=total_files,
            total_bytes=total_bytes,
            total_readable=format_bytes_readable(total_bytes),
            checksum=snapshot_checksum,
            notes=notes,
        )

    def list_backups(self, limit: int = 50, offset: int = 0) -> BackupHistoryResponse:
        """Retrieve chronological audit list of backup snapshots."""
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM backups")
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT id, status, snapshot_timestamp, total_files, total_bytes, checksum, notes
            FROM backups
            ORDER BY snapshot_timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()

        snapshots = [
            BackupSnapshotResponse(
                id=row["id"],
                status=row["status"],
                snapshot_timestamp=str(row["snapshot_timestamp"]),
                total_files=row["total_files"],
                total_bytes=row["total_bytes"],
                total_readable=format_bytes_readable(row["total_bytes"]),
                checksum=row["checksum"],
                notes=row["notes"],
            )
            for row in rows
        ]

        return BackupHistoryResponse(
            snapshots=snapshots,
            total=total,
        )
