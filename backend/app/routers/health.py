"""Health and operational diagnostic router."""

from datetime import datetime, timezone
import sqlite3
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.db.database import get_db
from app.models.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="System Health Check")
async def health_check(db: sqlite3.Connection = Depends(get_db)):
    """Verifies backend liveness, SQLite database access, and active storage driver."""
    db_status = "connected"
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
    except Exception:
        db_status = "unavailable"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        storage_provider=settings.STORAGE_PROVIDER,
        database_status=db_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
