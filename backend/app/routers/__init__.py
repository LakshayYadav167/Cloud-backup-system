"""Routers package initialization."""

from app.routers.health import router as health_router
from app.routers.files import router as files_router
from app.routers.storage import router as storage_router
from app.routers.backups import router as backups_router

__all__ = [
    "health_router",
    "files_router",
    "storage_router",
    "backups_router",
]
