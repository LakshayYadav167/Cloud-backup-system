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

    # Check active storage driver availability
    storage_status = "ready"
    if settings.STORAGE_PROVIDER.lower() == "s3":
        try:
            from app.storage.s3 import S3CompatibleStorage
            driver = S3CompatibleStorage(auto_create_bucket=False)
            if not driver.is_available():
                storage_status = "unavailable"
        except Exception:
            storage_status = "unavailable"
    elif settings.STORAGE_PROVIDER.lower() == "local":
        try:
            p = settings.storage_path_resolved
            if not p.exists() or not p.is_dir():
                storage_status = "unavailable"
        except Exception:
            storage_status = "unavailable"
    else:
        storage_status = "unsupported"

    is_healthy = db_status == "connected" and storage_status == "ready"

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        storage_provider=settings.STORAGE_PROVIDER,
        database_status=db_status,
        storage_status=storage_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
