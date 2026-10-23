"""Cloud Backup System - FastAPI Entry Point.

Zero-cost, modular file storage and versioned backup management API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.database import init_db
from app.routers import (
    backups_router,
    files_router,
    health_router,
    storage_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: directory setup, database initialization, teardown."""
    # Ensure storage directory exists on startup
    settings.storage_path_resolved
    # Initialize SQLite tables and indexes idempotently
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise-grade, zero-budget cloud backup and storage system. "
        "Built with FastAPI, SQLite, and an abstract storage provider layer (Local & S3/MinIO). "
        "Note: Designed as a single-user local demonstration system without multi-user auth."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS) for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent leaking stack traces or host paths."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Check server logs."},
    )


# Register versioned routers under /api/v1 namespace
app.include_router(health_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(storage_router, prefix="/api/v1")
app.include_router(backups_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint welcoming API consumers and pointing to interactive docs."""
    return {
        "project": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_check": "/api/v1/health",
        "api_v1_endpoints": {
            "health": "/api/v1/health",
            "files": "/api/v1/files",
            "upload": "/api/v1/files/upload",
            "storage_stats": "/api/v1/storage/stats",
            "backups_trigger": "/api/v1/backups/trigger",
            "backups_history": "/api/v1/backups/history",
        },
        "storage_mode": settings.STORAGE_PROVIDER,
        "message": "Cloud Backup System API is running successfully.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
