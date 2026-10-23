"""Cloud Backup System - FastAPI Entry Point.

Zero-cost, modular file storage and backup management API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: directory setup, db verification, teardown."""
    # Ensure storage directory exists on startup
    settings.storage_path_resolved
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise-grade, zero-budget cloud backup and storage system. "
        "Built with FastAPI, SQLite, and an abstract storage provider layer."
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

# Register routers under /api/v1 namespace
app.include_router(health_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint welcoming API consumers and pointing to interactive docs."""
    return {
        "project": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_check": "/api/v1/health",
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
