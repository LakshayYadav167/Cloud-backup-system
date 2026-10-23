"""Unit tests verifying the StorageProvider abstract base class contract."""

from io import BytesIO
from typing import BinaryIO, Dict, Optional
import pytest

from app.storage.base import (
    StorageItemInfo,
    StorageProvider,
    StorageStatsInfo,
)


def test_cannot_instantiate_abstract_storage_provider():
    """Attempting to instantiate StorageProvider directly must raise TypeError."""
    with pytest.raises(TypeError):
        StorageProvider()  # type: ignore


def test_concrete_implementation_fulfills_contract():
    """A concrete class that implements all abstract methods can be instantiated."""

    class DummyStorage(StorageProvider):
        def save_file(
            self,
            file_id: str,
            content: BinaryIO,
            metadata: Optional[Dict[str, str]] = None,
        ) -> StorageItemInfo:
            return StorageItemInfo(
                file_id=file_id,
                stored_path_or_key="dummy_path",
                size_bytes=100,
                sha256_checksum="dummy_checksum",
            )

        def get_file(self, file_id: str) -> BinaryIO:
            return BytesIO(b"dummy content")

        def delete_file(self, file_id: str) -> bool:
            return True

        def file_exists(self, file_id: str) -> bool:
            return True

        def get_storage_stats(self) -> StorageStatsInfo:
            return StorageStatsInfo(
                provider_name="dummy",
                total_files=1,
                total_bytes=100,
                base_location="/dummy",
            )

    driver = DummyStorage()
    assert driver.file_exists("123") is True
    stats = driver.get_storage_stats()
    assert stats.provider_name == "dummy"
    assert stats.total_files == 1
