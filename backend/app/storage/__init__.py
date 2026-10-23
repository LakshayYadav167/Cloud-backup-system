"""Storage package initialization and factory."""

from typing import Optional
from app.core.config import settings
from app.storage.base import StorageItemInfo, StorageProvider, StorageStatsInfo
from app.storage.local import LocalFileSystemStorage
from app.storage.s3 import S3CompatibleStorage

_cached_provider: Optional[StorageProvider] = None


def get_storage_provider(provider_type: Optional[str] = None) -> StorageProvider:
    """Factory to get the configured storage provider instance.

    Supported provider types: 'local' (default) and 's3'.
    """
    selected = (provider_type or settings.STORAGE_PROVIDER).lower()

    if selected == "s3":
        return S3CompatibleStorage()
    elif selected == "local":
        return LocalFileSystemStorage()
    else:
        raise ValueError(
            f"Unsupported storage provider: '{selected}'. Must be 'local' or 's3'."
        )


__all__ = [
    "StorageProvider",
    "StorageItemInfo",
    "StorageStatsInfo",
    "LocalFileSystemStorage",
    "S3CompatibleStorage",
    "get_storage_provider",
]
