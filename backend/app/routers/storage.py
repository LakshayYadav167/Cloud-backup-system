"""Storage metrics and capacity router."""

import sqlite3
from fastapi import APIRouter, Depends

from app.db.database import get_db
from app.models.schemas import StorageStatsResponse
from app.services.stats_service import StatsService

router = APIRouter(prefix="/storage", tags=["Storage Metrics"])


@router.get("/stats", response_model=StorageStatsResponse, summary="Get Storage Statistics")
async def get_storage_stats(db: sqlite3.Connection = Depends(get_db)):
    """Retrieves aggregated disk usage, tracked file count, and quota statistics."""
    service = StatsService(db)
    return service.get_stats()
