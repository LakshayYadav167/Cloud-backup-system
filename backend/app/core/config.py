"""Application configuration module for Cloud Backup System.

Supports environment variables with sensible zero-cost defaults.
"""

from pathlib import Path
from typing import List
import os

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field

    class Settings(BaseSettings):
        APP_NAME: str = Field(default="Cloud Backup System API")
        APP_VERSION: str = Field(default="1.0.0")
        APP_ENV: str = Field(default="development")
        DEBUG: bool = Field(default=True)

        HOST: str = Field(default="127.0.0.1")
        PORT: int = Field(default=8000)

        DATABASE_URL: str = Field(default="sqlite:///./data/cloud_backup.db")

        STORAGE_PROVIDER: str = Field(default="local")
        LOCAL_STORAGE_PATH: str = Field(default="./data/storage")
        MAX_UPLOAD_SIZE_MB: int = Field(default=50)

        CORS_ORIGINS: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

        @property
        def parsed_cors_origins(self) -> List[str]:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

        @property
        def storage_path_resolved(self) -> Path:
            p = Path(self.LOCAL_STORAGE_PATH)
            p.mkdir(parents=True, exist_ok=True)
            return p

    settings = Settings()

except ImportError:
    # Graceful fallback when dependencies are not yet installed in host environment
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

    settings = FallbackSettings()  # type: ignore
