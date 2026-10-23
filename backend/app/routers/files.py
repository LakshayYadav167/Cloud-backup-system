"""File operations router: upload, list, download, versioning, restore, and deletion."""

import sqlite3
from typing import List, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.db.database import get_db
from app.models.schemas import (
    FileDeleteResponse,
    FileItemResponse,
    FileListResponse,
    FileRestoreResponse,
    FileUploadResponse,
    FileVersionSummary,
)
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files & Versions"])


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload File (New or New Version)",
)
async def upload_file(
    file: UploadFile = File(..., description="Multipart file stream to upload"),
    summary: Optional[str] = Form(None, description="Optional change summary or notes for this version"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Uploads a file.

    If a file with the same filename already exists, a new immutable version is
    automatically created and linked, preserving previous historical versions.
    """
    service = FileService(db)
    return service.upload_file(file, custom_summary=summary)


@router.get(
    "",
    response_model=FileListResponse,
    summary="List Files",
)
async def list_files(
    search: Optional[str] = Query(None, description="Substring search filter on filename"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Lists files with metadata, current version details, and pagination."""
    service = FileService(db)
    return service.list_files(search=search, limit=limit, offset=offset)


@router.get(
    "/{file_id}",
    response_model=FileItemResponse,
    summary="Get File Metadata",
)
async def get_file_metadata(
    file_id: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Retrieves metadata and current version details for a single logical file."""
    service = FileService(db)
    return service.get_file_by_id(file_id)


@router.get(
    "/{file_id}/versions",
    response_model=List[FileVersionSummary],
    summary="List Historical Backup Versions",
)
async def list_file_versions(
    file_id: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Lists all historical backup versions for a file in descending order."""
    service = FileService(db)
    return service.list_file_versions(file_id)


@router.get(
    "/{file_id}/download",
    summary="Download File Content",
)
async def download_file(
    file_id: str,
    version_id: Optional[str] = Query(
        None, description="Specific version ID to download (defaults to current version)"
    ),
    db: sqlite3.Connection = Depends(get_db),
):
    """Streams file content. Supports downloading the current version or any historical version."""
    service = FileService(db)
    stream, filename, content_type, size_bytes, sha256 = service.get_file_content_stream(
        file_id=file_id, version_id=version_id
    )

    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}",
        "Content-Length": str(size_bytes),
        "ETag": f'"{sha256}"',
    }

    return StreamingResponse(
        stream,
        media_type=content_type,
        headers=headers,
    )


@router.post(
    "/{file_id}/restore/{version_id}",
    response_model=FileRestoreResponse,
    summary="Restore Previous Version",
)
async def restore_version(
    file_id: str,
    version_id: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Rolls back the current version of a file to a specified historical version.

    The historical content and version records remain intact and immutable.
    """
    service = FileService(db)
    return service.restore_file_version(file_id=file_id, version_id=version_id)


@router.delete(
    "/{file_id}",
    response_model=FileDeleteResponse,
    summary="Delete File",
)
async def delete_file(
    file_id: str,
    db: sqlite3.Connection = Depends(get_db),
):
    """Permanently removes a file, all historical versions, and their stored objects."""
    service = FileService(db)
    service.delete_file(file_id)
    return FileDeleteResponse(
        success=True,
        message="File and all historical versions deleted successfully.",
        file_id=file_id,
    )
