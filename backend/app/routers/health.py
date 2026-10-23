"""Health and status check router."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="System Health Check")
async def health_check():
    """Returns application health, version, and active storage provider."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "storage_provider": settings.STORAGE_PROVIDER,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
