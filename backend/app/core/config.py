"""Application configuration module for Cloud Backup System.

Supports environment variables with sensible zero-cost defaults.
"""

from pathlib import Path
from typing import List, Optional
import os

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        APP_NAME: str = Field(default="Cloud Backup System API")
        APP_VERSION: str = Field(default="1.0.0")
        APP_ENV: str = Field(default="development")
        DEBUG: bool = Field(default=True)

        HOST: str = Field(default="127.0.0.1")
        PORT: int = Field(default=8000)

        DATABASE_URL: str = Field(default="sqlite:///./data/cloud_backup.db")

        # Storage Provider Configuration: "local" or "s3"
        STORAGE_PROVIDER: str = Field(default="local")
        LOCAL_STORAGE_PATH: str = Field(default="./data/storage")
        MAX_UPLOAD_SIZE_MB: int = Field(default=50)

        # Optional S3 / MinIO Configuration (for local S3-compatible service)
        S3_ENDPOINT_URL: Optional[str] = Field(default=None)
        S3_ACCESS_KEY: str = Field(default="minioadmin")
        S3_SECRET_KEY: str = Field(default="minioadmin")
        S3_BUCKET_NAME: str = Field(default="cloud-backup-system")
        S3_REGION: str = Field(default="us-east-1")
        S3_USE_SSL: bool = Field(default=False)

        CORS_ORIGINS: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

        @property
        def parsed_cors_origins(self) -> List[str]:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

        @property
        def storage_path_resolved(self) -> Path:
            p = Path(self.LOCAL_STORAGE_PATH)
            p.mkdir(parents=True, exist_ok=True)
            return p

        @property
        def max_upload_size_bytes(self) -> int:
            return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    settings = Settings()

except ImportError:
    # Graceful fallback when pydantic-settings is not available
    class FallbackSettings:
        APP_NAME: str = os.getenv("APP_NAME", "Cloud Backup System API")
        APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        APP_ENV: str = os.getenv("APP_ENV", "development")
        DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1")

        HOST: str = os.getenv("HOST", "127.0.0.1")
        PORT: int = int(os.getenv("PORT", "8000"))

        DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/cloud_backup.db")

        STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
        LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./data/storage")
        MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

        S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")
        S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
        S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
        S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "cloud-backup-system")
        S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
        S3_USE_SSL: bool = os.getenv("S3_USE_SSL", "false").lower() in ("true", "1")

        CORS_ORIGINS: str = os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )

        @property
        def parsed_cors_origins(self) -> List[str]:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

        @property
        def storage_path_resolved(self) -> Path:
            p = Path(self.LOCAL_STORAGE_PATH)
            p.mkdir(parents=True, exist_ok=True)
            return p

        @property
        def max_upload_size_bytes(self) -> int:
            return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    settings = FallbackSettings()  # type: ignore
