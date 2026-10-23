"""Storage provider abstraction layer.

Defines the abstract interface for storage drivers (Local Filesystem,
S3 / MinIO compatible object storage).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO, Dict, Optional


@dataclass
class StorageItemInfo:
    """Standardized metadata returned after persisting a file."""
    stored_path_or_key: str
    size_bytes: int
    sha256_checksum: str
    object_key: str = ""
    file_id: str = ""

    def __post_init__(self):
        if not self.object_key:
            self.object_key = self.stored_path_or_key
        if not self.file_id:
            self.file_id = self.object_key


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
        object_key: str,
        content: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageItemInfo:
        """Persist a file stream under a unique object key and return metadata.

        Args:
            object_key: Safe unique identifier or path token for the object.
            content: Readable binary stream.
            metadata: Optional dictionary of key/value tags.

        Returns:
            StorageItemInfo with storage location, size, and SHA-256 checksum.
        """
        pass

    @abstractmethod
    def get_file(self, object_key: str) -> BinaryIO:
        """Retrieve a readable binary stream of the stored object.

        Args:
            object_key: Unique identifier for the object.

        Returns:
            Readable BinaryIO stream.

        Raises:
            FileNotFoundError if the target object does not exist.
        """
        pass

    @abstractmethod
    def delete_file(self, object_key: str) -> bool:
        """Permanently remove a stored object.

        Args:
            object_key: Unique identifier for the object.

        Returns:
            True if deleted, False if object did not exist.
        """
        pass

    @abstractmethod
    def file_exists(self, object_key: str) -> bool:
        """Check if an object exists in the storage provider.

        Args:
            object_key: Unique identifier for the object.

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
