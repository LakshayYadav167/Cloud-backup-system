"""Portable backup archive management router.

Provides endpoints to:
1. Export complete, self-contained ZIP backup archives with version histories.
2. Verify archive structure, manifest integrity, and cryptographic SHA-256 hashes.
3. Atomically restore/import archives into the active storage and database tier.
"""

from io import BytesIO
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.db.database import get_db
from app.models.schemas import ArchiveRestoreResponse, ArchiveVerificationResponse
from app.services.archive_service import ArchiveService

router = APIRouter(prefix="/archives", tags=["Backup Archives"])


@router.get(
    "/export",
    summary="Export Portable Backup Archive (.zip)",
    response_description="Binary ZIP stream containing all files, historical versions, and manifest.json",
)
@router.post(
    "/export",
    summary="Export Portable Backup Archive (.zip)",
    response_description="Binary ZIP stream containing all files, historical versions, and manifest.json",
)
async def export_archive(
    notes: Optional[str] = Query(None, description="Optional audit notes to embed in manifest.json"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Generates an independently restorable, self-contained ZIP archive.

    Contains:
    - Root manifest.json with file relationships, version numbers, and SHA-256 hashes.
    - Full payload binary streams for all versions under blobs/.
    - Compatible with both local filesystem storage and S3/Floci object storage.
    """
    service = ArchiveService(db)
    zip_buffer, filename = service.export_archive(notes=notes)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.post(
    "/verify",
    response_model=ArchiveVerificationResponse,
    summary="Verify Backup Archive Integrity",
)
async def verify_archive(
    file: UploadFile = File(..., description="ZIP archive file to verify"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Inspects and validates an uploaded archive without modifying application state.

    Verifies:
    - Path traversal protection (rejects dangerous relative paths, absolute paths, and Windows drive roots).
    - Decompression limits (zip-bomb protection).
    - Presence, format version, and syntax of manifest.json.
    - Exact byte size and SHA-256 checksum verification for every included payload blob.
    """
    service = ArchiveService(db)
    return service.verify_archive(file)


@router.post(
    "/restore",
    response_model=ArchiveRestoreResponse,
    summary="Restore from Backup Archive",
)
async def restore_archive(
    file: UploadFile = File(..., description="Verified ZIP archive file to import"),
    conflict_strategy: str = Form(
        "rename",
        description="Collision strategy for duplicate filenames: 'rename', 'skip', or 'replace'",
    ),
    db: sqlite3.Connection = Depends(get_db),
):
    """Imports files and complete version histories from an archive into the active system.

    Guarantees:
    - Executes full cryptographic verification prior to making any changes.
    - Generates new system UUIDs (never trusts archive-supplied IDs).
    - Safely handles duplicate filename collisions using the selected conflict strategy.
    - Interrupted restores or storage failures trigger a clean rollback.
    """
    service = ArchiveService(db)
    return service.restore_archive(file, conflict_strategy=conflict_strategy)
