"""Domain service managing portable, self-contained backup archives.

Implements standard ZIP-based backup archives containing:
- manifest.json: versioned metadata, file relationships, and SHA-256 checksums
- blobs/: content-addressed or safely namespaced original file payload streams

Security controls:
- ZIP path traversal prevention (rejects '..', absolute paths, Windows drive roots)
- Decompression bomb protection (ratio limits, max uncompressed size, max entry limits)
- Non-trust of archive identifiers (generates new system UUIDs and storage keys)
- Full cryptographic SHA-256 integrity verification before modifying state
- Multi-backend compatibility (restores via StorageProvider abstraction)
"""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Set, Tuple
import hashlib
import json
import os
import re
import sqlite3
import uuid
import zipfile

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.schemas import ArchiveRestoreResponse, ArchiveVerificationResponse
from app.services.backup_service import format_bytes_readable
from app.services.file_service import RESERVED_NAMES, sanitize_filename
from app.storage import get_storage_provider
from app.storage.base import StorageProvider

# Archive specification constants
CURRENT_ARCHIVE_FORMAT_VERSION = "1.0.0"
SUPPORTED_FORMAT_VERSIONS: Set[str] = {CURRENT_ARCHIVE_FORMAT_VERSION}

# Security limits for imported archives
MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024       # 100 MB max archive upload
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024       # 250 MB max total uncompressed payload
MAX_ENTRY_COUNT = 1000                           # Max files inside archive
MAX_COMPRESSION_RATIO = 100.0                    # Max uncompressed / compressed ratio


def validate_zip_entry_name(entry_name: str) -> None:
    """Validate archive entry path against directory traversal and dangerous characters.

    Raises ValueError if the path violates security constraints.
    """
    if not entry_name or not entry_name.strip():
        raise ValueError("Archive contains an empty entry name.")

    # Disallow backslashes, null bytes, or control characters
    if "\\" in entry_name or "\x00" in entry_name or any(ord(c) < 32 for c in entry_name):
        raise ValueError(f"Entry '{entry_name}' contains illegal path separators or control characters.")

    # Disallow leading slashes or absolute path specifiers
    if entry_name.startswith("/"):
        raise ValueError(f"Entry '{entry_name}' uses an illegal absolute path.")

    # Disallow Windows drive prefixes (e.g. 'C:', 'D:')
    if re.match(r"^[a-zA-Z]:", entry_name):
        raise ValueError(f"Entry '{entry_name}' contains a Windows drive specification.")

    parts = entry_name.split("/")
    for part in parts:
        if part in (".", ".."):
            raise ValueError(f"Directory traversal token '{part}' detected in entry '{entry_name}'.")
        if not part:
            # Trailing or duplicate slash
            continue

        # Check for reserved device names
        stem = Path(part).stem.upper()
        if stem in RESERVED_NAMES:
            raise ValueError(f"Entry '{entry_name}' contains reserved system device name '{part}'.")

    if len(entry_name) > 255:
        raise ValueError(f"Entry name exceeds maximum path length of 255 characters: '{entry_name[:30]}...'")


class ArchiveService:
    """Service managing portable archive export, cryptographic verification, and safe restoration."""

    def __init__(self, db: sqlite3.Connection, storage: Optional[StorageProvider] = None):
        self.db = db
        self.storage = storage or get_storage_provider()

    # --------------------------------------------------------------------------
    # 1. Export Portable Archive
    # --------------------------------------------------------------------------
    def export_archive(self, notes: Optional[str] = None) -> Tuple[BytesIO, str]:
        """Export all active files and their complete version histories into a portable ZIP archive.

        Returns: (zip_buffer, download_filename)
        Raises:
            HTTPException(409) if an active file's physical object is missing from storage.
        """
        cursor = self.db.cursor()

        # Query active logical files in consistent order
        cursor.execute(
            """
            SELECT id, filename, content_type, current_version_id, created_at, updated_at
            FROM files
            WHERE is_deleted = 0
            ORDER BY filename ASC, id ASC
            """
        )
        file_rows = cursor.fetchall()

        manifest_files: List[Dict] = []
        blobs_to_pack: List[Dict] = []
        total_versions = 0
        total_bytes = 0

        # Collect versions and verify physical object presence
        for f_row in file_rows:
            f_id = f_row["id"]
            filename = f_row["filename"]
            safe_fname = sanitize_filename(filename)

            cursor.execute(
                """
                SELECT id, version_number, object_key, size_bytes, sha256,
                       content_type, change_summary, created_at
                FROM file_versions
                WHERE file_id = ?
                ORDER BY version_number ASC
                """,
                (f_id,),
            )
            v_rows = cursor.fetchall()

            version_entries: List[Dict] = []
            for v_row in v_rows:
                v_id = v_row["id"]
                obj_key = v_row["object_key"]
                v_num = v_row["version_number"]
                size_bytes = v_row["size_bytes"]
                sha256 = v_row["sha256"]
                is_curr = (v_id == f_row["current_version_id"])

                # Check that object physically exists in storage backend
                try:
                    if not self.storage.file_exists(obj_key):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Cannot export complete archive: storage object for file '{filename}' "
                                f"(version {v_num}) is missing from the active storage backend."
                            ),
                        )
                except Exception as check_err:
                    if isinstance(check_err, HTTPException):
                        raise check_err
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Storage driver failed during object verification: {str(check_err)}",
                    )

                archive_path = f"blobs/{v_id}_{safe_fname}"

                version_entries.append(
                    {
                        "id": v_id,
                        "version_number": v_num,
                        "size_bytes": size_bytes,
                        "sha256": sha256,
                        "content_type": v_row["content_type"],
                        "change_summary": v_row["change_summary"],
                        "created_at": str(v_row["created_at"]),
                        "is_current": is_curr,
                        "archive_path": archive_path,
                    }
                )

                blobs_to_pack.append(
                    {
                        "object_key": obj_key,
                        "archive_path": archive_path,
                        "expected_sha256": sha256,
                        "expected_size": size_bytes,
                        "filename": filename,
                    }
                )

                total_versions += 1
                total_bytes += size_bytes

            current_v_num = next(
                (v["version_number"] for v in version_entries if v["id"] == f_row["current_version_id"]),
                len(version_entries),
            )

            manifest_files.append(
                {
                    "id": f_id,
                    "filename": filename,
                    "content_type": f_row["content_type"],
                    "current_version_id": f_row["current_version_id"],
                    "current_version_number": current_v_num,
                    "created_at": str(f_row["created_at"]),
                    "updated_at": str(f_row["updated_at"]),
                    "versions": version_entries,
                }
            )

        # Assemble manifest document
        now_utc = datetime.now(timezone.utc).isoformat()
        manifest_data = {
            "archive_format_version": CURRENT_ARCHIVE_FORMAT_VERSION,
            "generator": "Cloud Backup System Portable Archive Engine",
            "exported_at": now_utc,
            "source_storage_provider": settings.STORAGE_PROVIDER,
            "notes": notes or f"Portable backup archive containing {len(file_rows)} files and {total_versions} versions",
            "total_files": len(file_rows),
            "total_versions": total_versions,
            "total_bytes": total_bytes,
            "files": manifest_files,
        }

        # Pack into in-memory ZIP buffer
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write manifest.json
            manifest_json_str = json.dumps(manifest_data, indent=2)
            zf.writestr("manifest.json", manifest_json_str)

            # Write individual version payloads
            for item in blobs_to_pack:
                try:
                    stream = self.storage.get_file(item["object_key"])
                    payload_bytes = stream.read()
                except Exception as read_err:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Failed to read file content for '{item['filename']}': {str(read_err)}",
                    )

                # Verify checksum before writing to archive
                actual_hash = hashlib.sha256(payload_bytes).hexdigest()
                if actual_hash != item["expected_sha256"]:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=(
                            f"Integrity check failed during export for '{item['filename']}': "
                            f"computed {actual_hash} != expected {item['expected_sha256']}"
                        ),
                    )

                zf.writestr(item["archive_path"], payload_bytes)

        zip_buffer.seek(0)
        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        download_filename = f"cloud_backup_archive_{timestamp_slug}.zip"

        return (zip_buffer, download_filename)

    # --------------------------------------------------------------------------
    # 2. Verify Archive
    # --------------------------------------------------------------------------
    def verify_archive(self, archive_file: UploadFile) -> ArchiveVerificationResponse:
        """Inspect and cryptographically verify an uploaded ZIP archive without modifying state.

        Validates:
        - Maximum archive size and entry count limits (zip-bomb defense)
        - Safe relative paths (path-traversal defense)
        - Presence and schema of manifest.json
        - Exact size and SHA-256 checksum match for every version payload
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Read into memory while enforcing size limit
        buffer = BytesIO()
        total_read = 0
        while True:
            chunk = archive_file.file.read(64 * 1024)
            if not chunk:
                break
            buffer.write(chunk)
            total_read += len(chunk)
            if total_read > MAX_ARCHIVE_SIZE_BYTES:
                return ArchiveVerificationResponse(
                    valid=False,
                    errors=[f"Archive size exceeds maximum permitted limit of {MAX_ARCHIVE_SIZE_BYTES // (1024 * 1024)} MB."],
                )

        if total_read == 0:
            return ArchiveVerificationResponse(valid=False, errors=["Uploaded archive is empty."])

        buffer.seek(0)

        # Check valid ZIP structure
        if not zipfile.is_zipfile(buffer):
            return ArchiveVerificationResponse(valid=False, errors=["Uploaded file is not a valid ZIP archive."])

        try:
            with zipfile.ZipFile(buffer, mode="r") as zf:
                infolist = zf.infolist()

                if len(infolist) > MAX_ENTRY_COUNT:
                    return ArchiveVerificationResponse(
                        valid=False,
                        errors=[f"Archive contains {len(infolist)} entries, exceeding safety limit of {MAX_ENTRY_COUNT}."],
                    )

                total_uncompressed = 0
                for info in infolist:
                    total_uncompressed += info.file_size

                    # Check compression ratio
                    compressed_size = max(info.compress_size, 1)
                    ratio = info.file_size / compressed_size
                    if ratio > MAX_COMPRESSION_RATIO:
                        return ArchiveVerificationResponse(
                            valid=False,
                            errors=[f"Suspicious compression ratio ({ratio:.1f}:1) detected for '{info.filename}' (zip-bomb protection)."],
                        )

                    # Validate path traversal
                    try:
                        validate_zip_entry_name(info.filename)
                    except ValueError as path_err:
                        return ArchiveVerificationResponse(valid=False, errors=[str(path_err)])

                if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                    return ArchiveVerificationResponse(
                        valid=False,
                        errors=[f"Total uncompressed size ({format_bytes_readable(total_uncompressed)}) exceeds limit of {format_bytes_readable(MAX_UNCOMPRESSED_BYTES)}."],
                    )

                namelist = set(zf.namelist())

                # Check manifest presence
                if "manifest.json" not in namelist:
                    return ArchiveVerificationResponse(
                        valid=False,
                        errors=["Archive does not contain a root 'manifest.json' file."],
                    )

                # Parse manifest
                try:
                    manifest_raw = zf.read("manifest.json").decode("utf-8")
                    manifest = json.loads(manifest_raw)
                except Exception as json_err:
                    return ArchiveVerificationResponse(
                        valid=False,
                        errors=[f"Failed to parse 'manifest.json': {str(json_err)}"],
                    )

                # Validate manifest structure and version
                fmt_version = manifest.get("archive_format_version")
                if not fmt_version:
                    errors.append("Manifest is missing 'archive_format_version'.")
                elif fmt_version not in SUPPORTED_FORMAT_VERSIONS:
                    errors.append(f"Unsupported archive format version '{fmt_version}'. Supported: {list(SUPPORTED_FORMAT_VERSIONS)}.")

                files = manifest.get("files")
                if not isinstance(files, list):
                    errors.append("Manifest 'files' key must be a list.")
                    files = []

                # Cross-verify all declared files and version blobs
                declared_paths: Set[str] = {"manifest.json"}
                actual_total_files = len(files)
                actual_total_versions = 0
                actual_total_bytes = 0

                for f_idx, f_entry in enumerate(files):
                    fname = f_entry.get("filename")
                    if not fname:
                        errors.append(f"File at index {f_idx} is missing a 'filename'.")
                        continue

                    versions = f_entry.get("versions", [])
                    if not isinstance(versions, list) or len(versions) == 0:
                        errors.append(f"File '{fname}' contains no versions.")
                        continue

                    for v_entry in versions:
                        actual_total_versions += 1
                        v_num = v_entry.get("version_number", 1)
                        expected_sha = v_entry.get("sha256")
                        expected_size = v_entry.get("size_bytes")
                        arch_path = v_entry.get("archive_path")

                        if not arch_path:
                            errors.append(f"File '{fname}' v{v_num} has no 'archive_path'.")
                            continue

                        declared_paths.add(arch_path)

                        if arch_path not in namelist:
                            errors.append(f"Payload blob '{arch_path}' declared in manifest is missing from archive.")
                            continue

                        # Extract payload and verify checksum & size
                        try:
                            blob_bytes = zf.read(arch_path)
                        except Exception as read_err:
                            errors.append(f"Failed to read '{arch_path}': {str(read_err)}")
                            continue

                        if len(blob_bytes) != expected_size:
                            errors.append(
                                f"Size mismatch for '{fname}' v{v_num}: "
                                f"manifest says {expected_size} bytes, got {len(blob_bytes)} bytes."
                            )

                        computed_sha = hashlib.sha256(blob_bytes).hexdigest()
                        if computed_sha != expected_sha:
                            errors.append(
                                f"Cryptographic checksum mismatch for '{fname}' v{v_num}: "
                                f"computed {computed_sha} != manifest {expected_sha}."
                            )

                        actual_total_bytes += len(blob_bytes)

                # Check for undeclared rogue entries in ZIP
                extra_entries = namelist - declared_paths
                if extra_entries:
                    warnings.append(
                        f"Archive contains {len(extra_entries)} extra unmanifested entries: {list(extra_entries)[:5]}."
                    )

                is_valid = len(errors) == 0

                return ArchiveVerificationResponse(
                    valid=is_valid,
                    format_version=fmt_version,
                    generator=manifest.get("generator"),
                    exported_at=manifest.get("exported_at"),
                    total_files=actual_total_files,
                    total_versions=actual_total_versions,
                    total_bytes=actual_total_bytes,
                    total_readable=format_bytes_readable(actual_total_bytes),
                    errors=errors,
                    warnings=warnings,
                )

        except Exception as zf_err:
            return ArchiveVerificationResponse(
                valid=False,
                errors=[f"Failed to inspect archive: {str(zf_err)}"],
            )

    # --------------------------------------------------------------------------
    # 3. Restore / Import Archive
    # --------------------------------------------------------------------------
    def restore_archive(
        self,
        archive_file: UploadFile,
        conflict_strategy: str = "rename",
    ) -> ArchiveRestoreResponse:
        """Atomically import an independently restorable backup archive into the active system.

        Conflict strategies:
        - "rename": Appends '_imported_<uuid>' to conflicting filenames (default, non-destructive).
        - "skip": Ignores any imported file whose filename already exists in the system.
        - "replace": Overwrites existing files and replaces all their versions with imported versions.

        Security guarantees:
        - Runs complete verification before any disk/DB modifications.
        - Does NOT trust original UUIDs: generates fresh system UUIDs.
        - Persists through the StorageProvider abstraction (works on Local & S3/Floci).
        - Rolls back all persisted files and database inserts if an error occurs.
        """
        valid_strategies = {"rename", "skip", "replace"}
        if conflict_strategy.lower() not in valid_strategies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid conflict strategy '{conflict_strategy}'. Must be one of: {list(valid_strategies)}.",
            )
        strategy = conflict_strategy.lower()

        # Step 1: Cryptographic and structural verification
        verification = self.verify_archive(archive_file)
        if not verification.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Archive verification failed. Import aborted to prevent data corruption.",
                    "errors": verification.errors,
                },
            )

        # Rewind buffer
        archive_file.file.seek(0)
        buffer = BytesIO(archive_file.file.read())

        imported_files_count = 0
        imported_versions_count = 0
        skipped_files_count = 0
        details: List[str] = []
        created_object_keys: List[str] = []
        old_storage_keys_to_delete: List[str] = []

        try:
            with zipfile.ZipFile(buffer, mode="r") as zf:
                manifest_raw = zf.read("manifest.json").decode("utf-8")
                manifest = json.loads(manifest_raw)
                files = manifest.get("files", [])

                # Entire database restoration runs within a single atomic transaction
                with self.db:
                    cursor = self.db.cursor()

                    for f_entry in files:
                        original_filename = sanitize_filename(f_entry["filename"])
                        content_type = f_entry.get("content_type", "application/octet-stream")
                        versions = f_entry.get("versions", [])

                        # Check for name collisions
                        cursor.execute(
                            "SELECT id FROM files WHERE filename = ? AND is_deleted = 0",
                            (original_filename,),
                        )
                        existing_row = cursor.fetchone()

                        target_filename = original_filename

                        if existing_row:
                            if strategy == "skip":
                                skipped_files_count += 1
                                details.append(f"Skipped '{original_filename}' (file already exists).")
                                continue
                            elif strategy == "rename":
                                short_slug = str(uuid.uuid4())[:8]
                                stem = Path(original_filename).stem
                                suffix = Path(original_filename).suffix
                                target_filename = f"{stem}_imported_{short_slug}{suffix}"
                                details.append(f"Renamed '{original_filename}' &rarr; '{target_filename}' (conflict resolution).")
                            elif strategy == "replace":
                                existing_file_id = existing_row["id"]
                                cursor.execute(
                                    "SELECT object_key FROM file_versions WHERE file_id = ?",
                                    (existing_file_id,),
                                )
                                old_keys = [r["object_key"] for r in cursor.fetchall()]
                                old_storage_keys_to_delete.extend(old_keys)

                                # Atomically delete database records
                                self.db.execute("DELETE FROM file_versions WHERE file_id = ?", (existing_file_id,))
                                self.db.execute("DELETE FROM files WHERE id = ?", (existing_file_id,))
                                details.append(f"Replaced existing file '{original_filename}'.")

                        # Generate brand new unique file ID
                        new_file_id = str(uuid.uuid4())
                        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                        # Insert parent logical file record (placeholder current_version_id updated after)
                        self.db.execute(
                            """
                            INSERT INTO files (id, filename, content_type, current_version_id, is_deleted, created_at, updated_at)
                            VALUES (?, ?, ?, NULL, 0, ?, ?)
                            """,
                            (new_file_id, target_filename, content_type, now_ts, now_ts),
                        )

                        new_current_version_id: Optional[str] = None
                        versions_sorted = sorted(versions, key=lambda v: v.get("version_number", 1))

                        for v_entry in versions_sorted:
                            v_num = v_entry.get("version_number", 1)
                            v_sha = v_entry.get("sha256")
                            v_mime = v_entry.get("content_type", content_type)
                            v_summary = v_entry.get("change_summary", "Restored from archive")
                            v_created = v_entry.get("created_at", now_ts)
                            is_active_version = v_entry.get("is_current", False)
                            arch_path = v_entry["archive_path"]

                            # Read payload from zip
                            blob_bytes = zf.read(arch_path)

                            # Generate new unique object key in target storage backend
                            new_version_id = str(uuid.uuid4())
                            new_object_key = f"imported_{new_version_id}_{target_filename}"

                            # Save into active storage provider
                            self.storage.save_file(new_object_key, BytesIO(blob_bytes))
                            created_object_keys.append(new_object_key)

                            # Record in database
                            self.db.execute(
                                """
                                INSERT INTO file_versions (
                                    id, file_id, version_number, object_key,
                                    size_bytes, sha256, content_type, change_summary, created_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    new_version_id,
                                    new_file_id,
                                    v_num,
                                    new_object_key,
                                    len(blob_bytes),
                                    v_sha,
                                    v_mime,
                                    v_summary,
                                    v_created,
                                ),
                            )

                            imported_versions_count += 1

                            if is_active_version or new_current_version_id is None:
                                new_current_version_id = new_version_id

                        # Update files table with target active current_version_id
                        self.db.execute(
                            """
                            UPDATE files
                            SET current_version_id = ?
                            WHERE id = ?
                            """,
                            (new_current_version_id, new_file_id),
                        )

                        imported_files_count += 1

            # Only after the entire transaction successfully commits do we purge old storage keys
            for old_key in old_storage_keys_to_delete:
                try:
                    self.storage.delete_file(old_key)
                except Exception:
                    pass

        except Exception as restore_err:
            # Rollback newly written physical objects
            for key in created_object_keys:
                try:
                    self.storage.delete_file(key)
                except Exception:
                    pass

            if isinstance(restore_err, HTTPException):
                raise restore_err

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Archive restoration failed halfway: {str(restore_err)}. Storage changes have been rolled back.",
            )

        return ArchiveRestoreResponse(
            success=True,
            message=f"Archive successfully imported: {imported_files_count} files ({imported_versions_count} versions) restored.",
            conflict_strategy=strategy,
            imported_files_count=imported_files_count,
            imported_versions_count=imported_versions_count,
            skipped_files_count=skipped_files_count,
            details=details,
        )
