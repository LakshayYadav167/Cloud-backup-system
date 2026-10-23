"""Backup snapshot management router."""

import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.db.database import get_db
from app.models.schemas import BackupHistoryResponse, BackupSnapshotResponse
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backups", tags=["Backup Snapshots"])


@router.post(
    "/trigger",
    response_model=BackupSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Backup Snapshot",
)
async def trigger_backup(
    notes: Optional[str] = Query(None, description="Optional description or reason for this snapshot"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Creates a point-in-time immutable backup snapshot of all active file versions."""
    service = BackupService(db)
    return service.trigger_backup(notes=notes)


@router.get(
    "/history",
    response_model=BackupHistoryResponse,
    summary="List Backup Snapshot History",
)
async def list_backup_history(
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Returns chronological audit log of all generated backup snapshots."""
    service = BackupService(db)
    return service.list_backups(limit=limit, offset=offset)
