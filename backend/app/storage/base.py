"""Storage provider abstraction layer.

This module defines the abstract contract that any storage driver (e.g.
Local FileSystem, MinIO, or S3-compatible storage) must implement. This
ensures the Cloud Backup System remains modular and decoupled from the
underlying physical persistence mechanism.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO, Dict, Optional


@dataclass
class StorageItemInfo:
    """Standardized metadata returned after persisting a file."""
    file_id: str
    stored_path_or_key: str
    size_bytes: int
    sha256_checksum: str


@dataclass
class StorageStatsInfo:
    """Aggregated capacity metrics reported by the active storage provider."""
    provider_name: str
    total_files: int
    total_bytes: int
    base_location: str


class StorageProvider(ABC):
    """Abstract Base Class for all Cloud Backup System storage providers."""

    @abstractmethod
    def save_file(
        self,
        file_id: str,
        content: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageItemInfo:
        """Persist a file stream and return standardized item metadata.

        Args:
            file_id: Unique identifier (UUID v4) for the file.
            content: Readable binary stream.
            metadata: Optional dictionary of key/value tags.

        Returns:
            StorageItemInfo with storage location, size, and checksum.
        """
        pass

    @abstractmethod
    def get_file(self, file_id: str) -> BinaryIO:
        """Retrieve a readable binary stream of the stored file.

        Args:
            file_id: Unique identifier for the file.

        Returns:
            Readable BinaryIO stream.

        Raises:
            FileNotFoundError if the target file does not exist.
        """
        pass

    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """Permanently remove a stored file.

        Args:
            file_id: Unique identifier for the file.

        Returns:
            True if deleted, False if file did not exist.
        """
        pass

    @abstractmethod
    def file_exists(self, file_id: str) -> bool:
        """Check if a file exists in the storage provider.

        Args:
            file_id: Unique identifier for the file.

        Returns:
            True if present, False otherwise.
        """
        pass

    @abstractmethod
    def get_storage_stats(self) -> StorageStatsInfo:
        """Compute aggregated storage statistics.

        Returns:
            StorageStatsInfo containing file count and byte footprint.
        """
        pass
