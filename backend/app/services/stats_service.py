"""Domain service calculating storage and quota consumption statistics."""

from typing import Optional
import sqlite3

from app.core.config import settings
from app.models.schemas import StorageStatsResponse
from app.services.backup_service import format_bytes_readable
from app.storage import get_storage_provider
from app.storage.base import StorageProvider


class StatsService:
    """Service layer aggregating storage usage and operational metrics."""

    def __init__(self, db: sqlite3.Connection, storage: Optional[StorageProvider] = None):
        self.db = db
        self.storage = storage or get_storage_provider()

    def get_stats(self) -> StorageStatsResponse:
        cursor = self.db.cursor()

        # Count active files
        cursor.execute("SELECT COUNT(*) AS total FROM files WHERE is_deleted = 0")
        total_files = cursor.fetchone()["total"]

        # Count versions and total bytes
        cursor.execute(
            "SELECT COUNT(*) AS total_versions, COALESCE(SUM(size_bytes), 0) AS total_bytes FROM file_versions"
        )
        row = cursor.fetchone()
        total_versions = row["total_versions"]
        total_bytes = row["total_bytes"]

        # Last backup timestamp
        cursor.execute(
            "SELECT snapshot_timestamp FROM backups ORDER BY snapshot_timestamp DESC LIMIT 1"
        )
        last_backup_row = cursor.fetchone()
        last_backup_at = (
            str(last_backup_row["snapshot_timestamp"]) if last_backup_row else None
        )

        quota_bytes = settings.max_upload_size_bytes
        quota_percent = (
            round((total_bytes / quota_bytes) * 100, 2) if quota_bytes > 0 else 0.0
        )

        # Storage driver metrics
        driver_stats = self.storage.get_storage_stats()
        # Security: mask absolute path to avoid leaking server user directories
        safe_location = (
            "./data/storage" if driver_stats.provider_name == "local" else driver_stats.base_location
        )

        return StorageStatsResponse(
            provider=driver_stats.provider_name,
            total_files=total_files,
            total_versions=total_versions,
            total_bytes=total_bytes,
            total_readable=format_bytes_readable(total_bytes),
            quota_bytes=quota_bytes,
            quota_readable=format_bytes_readable(quota_bytes),
            quota_percent_used=quota_percent,
            base_location=safe_location,
            last_backup_at=last_backup_at,
        )
