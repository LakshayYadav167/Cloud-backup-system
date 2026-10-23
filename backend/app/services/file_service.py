"""Domain service handling versioned file persistence, metadata, and retrieval."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple
import hashlib
import mimetypes
import os
import re
import sqlite3
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.schemas import (
    FileItemResponse,
    FileListResponse,
    FileRestoreResponse,
    FileUploadResponse,
    FileVersionSummary,
)
from app.storage import get_storage_provider
from app.storage.base import StorageProvider

# Windows reserved device names
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


def sanitize_filename(filename: Optional[str]) -> str:
    """Validate and sanitize untrusted user filename.

    Prevents directory traversal, command injection, and reserved Windows device names.
    """
    if filename is None or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty or whitespace only.",
        )

    # Strip null bytes and normalize slashes
    clean = filename.replace("\x00", "").replace("\\", "/")
    # Extract only the base name (no directory paths allowed)
    clean = os.path.basename(clean).strip()

    if not clean or clean in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename supplied.",
        )

    # Check for reserved Windows filenames (e.g., 'con.txt', 'aux.png')
    stem = Path(clean).stem.upper()
    if stem in RESERVED_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename '{clean}' uses a reserved system device name.",
        )

    # Remove dangerous characters, allow alphanumerics, hyphens, underscores, dots
    clean = re.sub(r'[<>:"/\\|?*]', '_', clean)
    if len(clean) > 255:
        # Truncate while keeping extension
        suffix = Path(clean).suffix
        clean = clean[:250 - len(suffix)] + suffix

    return clean


class FileService:
    """Service layer managing file uploads, versioning, downloads, and deletions."""

    def __init__(self, db: sqlite3.Connection, storage: Optional[StorageProvider] = None):
        self.db = db
        self.storage = storage or get_storage_provider()

    def upload_file(
        self,
        upload_file: UploadFile,
        custom_summary: Optional[str] = None,
    ) -> FileUploadResponse:
        """Stream and persist an uploaded file, creating a new logical file or a new version."""
        raw_filename = upload_file.filename
        safe_filename = sanitize_filename(raw_filename)

        # Detect or guess content type
        content_type = upload_file.content_type
        if not content_type or content_type == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(safe_filename)
            content_type = guessed or "application/octet-stream"

        # Read into buffer while validating size and computing SHA-256
        buffer = BytesIO()
        hasher = hashlib.sha256()
        total_bytes = 0
        max_bytes = settings.max_upload_size_bytes

        while True:
            chunk = upload_file.file.read(64 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=(
                        f"File size exceeds the configured upload limit of "
                        f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                    ),
                )
            buffer.write(chunk)
            hasher.update(chunk)

        buffer.seek(0)
        checksum = hasher.hexdigest()

        # Check if active logical file with this filename already exists
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, current_version_id FROM files WHERE filename = ? AND is_deleted = 0",
            (safe_filename,),
        )
        existing_file = cursor.fetchone()

        version_id = str(uuid.uuid4())

        if existing_file:
            file_id = existing_file["id"]
            # Find the latest version number
            cursor.execute(
                "SELECT MAX(version_number) AS max_v FROM file_versions WHERE file_id = ?",
                (file_id,),
            )
            row = cursor.fetchone()
            version_number = (row["max_v"] or 1) + 1
            change_summary = custom_summary or f"Updated version {version_number}"
            is_new = False
        else:
            file_id = str(uuid.uuid4())
            version_number = 1
            change_summary = custom_summary or "Initial upload"
            is_new = True

        # Generate an immutable, unique object key for this version
        # Format: files/{file_id}/{version_id}_{safe_filename}
        object_key = f"files/{file_id}/{version_id}_{safe_filename}"

        # Persist content using the active StorageProvider
        try:
            self.storage.save_file(
                object_key=object_key,
                content=buffer,
                metadata={
                    "file_id": file_id,
                    "version_id": version_id,
                    "filename": safe_filename,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage provider failed to save file: {str(e)}",
            )

        # Transactional SQLite commit with rollback on failure
        try:
            with self.db:
                if is_new:
                    self.db.execute(
                        """
                        INSERT INTO files (id, filename, content_type, current_version_id, is_deleted)
                        VALUES (?, ?, ?, ?, 0)
                        """,
                        (file_id, safe_filename, content_type, version_id),
                    )
                else:
                    self.db.execute(
                        """
                        UPDATE files
                        SET current_version_id = ?, content_type = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (version_id, content_type, file_id),
                    )

                self.db.execute(
                    """
                    INSERT INTO file_versions (
                        id, file_id, version_number, object_key, size_bytes,
                        sha256, content_type, change_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        file_id,
                        version_number,
                        object_key,
                        total_bytes,
                        checksum,
                        content_type,
                        change_summary,
                    ),
                )
        except Exception as db_err:
            # Rollback: Clean up newly stored object from storage to prevent orphan files
            self.storage.delete_file(object_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction failed during file registration.",
            )

        # Retrieve file response
        file_resp = self.get_file_by_id(file_id)
        version_summary = FileVersionSummary(
            id=version_id,
            file_id=file_id,
            version_number=version_number,
            size_bytes=total_bytes,
            sha256=checksum,
            content_type=content_type,
            change_summary=change_summary,
            created_at=file_resp.updated_at,
            is_current=True,
        )

        msg = (
            f"File '{safe_filename}' uploaded successfully as version {version_number}."
            if not is_new
            else f"File '{safe_filename}' uploaded successfully."
        )

        return FileUploadResponse(
            file=file_resp,
            version=version_summary,
            message=msg,
        )

    def list_files(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> FileListResponse:
        """Query files with optional substring search and pagination."""
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        query_conditions = ["f.is_deleted = 0"]
        params: List[str] = []

        if search and search.strip():
            query_conditions.append("f.filename LIKE ?")
            params.append(f"%{search.strip()}%")

        where_clause = " WHERE " + " AND ".join(query_conditions)

        count_sql = f"SELECT COUNT(*) AS total FROM files f {where_clause}"
        cursor = self.db.cursor()
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]

        list_sql = f"""
            SELECT
                f.id,
                f.filename,
                f.content_type,
                f.created_at,
                f.updated_at,
                v.id AS current_version_id,
                v.version_number AS current_version_number,
                v.size_bytes,
                v.sha256,
                (SELECT COUNT(*) FROM file_versions WHERE file_id = f.id) AS total_versions
            FROM files f
            JOIN file_versions v ON f.current_version_id = v.id
            {where_clause}
            ORDER BY f.updated_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(list_sql, params + [limit, offset])
        rows = cursor.fetchall()

        items = [
            FileItemResponse(
                id=row["id"],
                filename=row["filename"],
                content_type=row["content_type"],
                size_bytes=row["size_bytes"],
                sha256=row["sha256"],
                current_version_id=row["current_version_id"],
                current_version_number=row["current_version_number"],
                total_versions=row["total_versions"],
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

        return FileListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_file_by_id(self, file_id: str) -> FileItemResponse:
        """Retrieve metadata for a specific logical file."""
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT
                f.id,
                f.filename,
                f.content_type,
                f.created_at,
                f.updated_at,
                v.id AS current_version_id,
                v.version_number AS current_version_number,
                v.size_bytes,
                v.sha256,
                (SELECT COUNT(*) FROM file_versions WHERE file_id = f.id) AS total_versions
            FROM files f
            JOIN file_versions v ON f.current_version_id = v.id
            WHERE f.id = ? AND f.is_deleted = 0
            """,
            (file_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID '{file_id}' not found.",
            )

        return FileItemResponse(
            id=row["id"],
            filename=row["filename"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            current_version_id=row["current_version_id"],
            current_version_number=row["current_version_number"],
            total_versions=row["total_versions"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_file_versions(self, file_id: str) -> List[FileVersionSummary]:
        """List all historical backup versions for a file."""
        # Check file exists
        file_item = self.get_file_by_id(file_id)

        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, file_id, version_number, size_bytes, sha256,
                   content_type, change_summary, created_at
            FROM file_versions
            WHERE file_id = ?
            ORDER BY version_number DESC
            """,
            (file_id,),
        )
        rows = cursor.fetchall()

        return [
            FileVersionSummary(
                id=row["id"],
                file_id=row["file_id"],
                version_number=row["version_number"],
                size_bytes=row["size_bytes"],
                sha256=row["sha256"],
                content_type=row["content_type"],
                change_summary=row["change_summary"],
                created_at=str(row["created_at"]),
                is_current=(row["id"] == file_item.current_version_id),
            )
            for row in rows
        ]

    def get_file_content_stream(
        self,
        file_id: str,
        version_id: Optional[str] = None,
    ) -> Tuple[BinaryIO, str, str, int, str]:
        """Fetch readable binary stream and file metadata for download.

        Returns: (stream, filename, content_type, size_bytes, sha256)
        """
        cursor = self.db.cursor()
        if version_id:
            cursor.execute(
                """
                SELECT f.filename, v.object_key, v.content_type, v.size_bytes, v.sha256
                FROM files f
                JOIN file_versions v ON f.id = v.file_id
                WHERE f.id = ? AND v.id = ? AND f.is_deleted = 0
                """,
                (file_id, version_id),
            )
        else:
            cursor.execute(
                """
                SELECT f.filename, v.object_key, v.content_type, v.size_bytes, v.sha256
                FROM files f
                JOIN file_versions v ON f.current_version_id = v.id
                WHERE f.id = ? AND f.is_deleted = 0
                """,
                (file_id,),
            )

        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target file or version not found.",
            )

        object_key = row["object_key"]
        try:
            stream = self.storage.get_file(object_key)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical object not found on storage backend.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve file from storage: {str(e)}",
            )

        return (
            stream,
            row["filename"],
            row["content_type"],
            row["size_bytes"],
            row["sha256"],
        )

    def restore_file_version(self, file_id: str, version_id: str) -> FileRestoreResponse:
        """Roll back the current version of a file to a previous historical version.

        Crucially: Preserves historical object keys and content immutability.
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, version_number, size_bytes, sha256, content_type, change_summary, created_at
            FROM file_versions
            WHERE file_id = ? AND id = ?
            """,
            (file_id, version_id),
        )
        target_version = cursor.fetchone()
        if not target_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version '{version_id}' does not exist for file '{file_id}'.",
            )

        # Update files current_version_id
        with self.db:
            self.db.execute(
                """
                UPDATE files
                SET current_version_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND is_deleted = 0
                """,
                (version_id, file_id),
            )

        updated_file = self.get_file_by_id(file_id)
        version_summary = FileVersionSummary(
            id=target_version["id"],
            file_id=file_id,
            version_number=target_version["version_number"],
            size_bytes=target_version["size_bytes"],
            sha256=target_version["sha256"],
            content_type=target_version["content_type"],
            change_summary=target_version["change_summary"],
            created_at=str(target_version["created_at"]),
            is_current=True,
        )

        return FileRestoreResponse(
            success=True,
            message=(
                f"File '{updated_file.filename}' restored to version "
                f"{target_version['version_number']}."
            ),
            file=updated_file,
            restored_version=version_summary,
        )

    def delete_file(self, file_id: str) -> bool:
        """Permanently delete a logical file and all of its historical versions."""
        cursor = self.db.cursor()
        # Find all stored object keys for this file
        cursor.execute(
            "SELECT object_key FROM file_versions WHERE file_id = ?",
            (file_id,),
        )
        version_keys = [row["object_key"] for row in cursor.fetchall()]

        if not version_keys:
            # Check if file row exists at all
            cursor.execute("SELECT id FROM files WHERE id = ?", (file_id,))
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File with ID '{file_id}' not found.",
                )

        # Delete physical objects from storage provider
        for key in version_keys:
            try:
                self.storage.delete_file(key)
            except Exception:
                pass

        # Delete database records (file_versions cascaded via foreign keys)
        with self.db:
            self.db.execute("DELETE FROM files WHERE id = ?", (file_id,))

        return True
