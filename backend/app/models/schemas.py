"""Pydantic schemas for request validation and response models."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    app_name: str
    version: str
    environment: str
    storage_provider: str
    database_status: str
    storage_status: Optional[str] = "ready"
    timestamp: str


class FileVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_id: str
    version_number: int
    size_bytes: int
    sha256: str
    content_type: str
    change_summary: str
    created_at: str
    is_current: bool = False


class FileItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    current_version_id: Optional[str] = None
    current_version_number: int = 1
    total_versions: int = 1
    created_at: str
    updated_at: str


class FileListResponse(BaseModel):
    items: List[FileItemResponse]
    total: int
    limit: int
    offset: int


class FileUploadResponse(BaseModel):
    file: FileItemResponse
    version: FileVersionSummary
    message: str


class FileRestoreResponse(BaseModel):
    success: bool
    message: str
    file: FileItemResponse
    restored_version: FileVersionSummary


class FileDeleteResponse(BaseModel):
    success: bool
    message: str
    file_id: str


class StorageStatsResponse(BaseModel):
    provider: str
    total_files: int
    total_versions: int
    total_bytes: int
    total_readable: str
    quota_bytes: int
    quota_readable: str
    quota_percent_used: float
    base_location: str
    last_backup_at: Optional[str] = None


class BackupSnapshotResponse(BaseModel):
    id: str
    status: str
    snapshot_timestamp: str
    total_files: int
    total_bytes: int
    total_readable: str
    checksum: Optional[str] = None
    notes: Optional[str] = None


class BackupHistoryResponse(BaseModel):
    snapshots: List[BackupSnapshotResponse]
    total: int


class ArchiveVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    valid: bool
    format_version: Optional[str] = None
    generator: Optional[str] = None
    exported_at: Optional[str] = None
    total_files: int = 0
    total_versions: int = 0
    total_bytes: int = 0
    total_readable: str = "0 B"
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ArchiveRestoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str
    conflict_strategy: str
    imported_files_count: int
    imported_versions_count: int
    skipped_files_count: int
    details: List[str] = Field(default_factory=list)

