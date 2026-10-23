"""Local filesystem storage provider implementation.

Zero-cost, reliable storage on the host filesystem with strict
path-traversal protection and atomic file writing.
"""

from pathlib import Path
from typing import BinaryIO, Dict, Optional
import hashlib
import os

from app.core.config import settings
from app.storage.base import StorageItemInfo, StorageProvider, StorageStatsInfo


class LocalFileSystemStorage(StorageProvider):
    """Local disk driver for the StorageProvider abstraction."""

    def __init__(self, base_path: Optional[str] = None):
        raw_path = base_path or settings.LOCAL_STORAGE_PATH
        self.base_path = Path(raw_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, object_key: str) -> Path:
        """Resolve an object key to a safe filesystem path within base_path.

        Prevents path traversal vulnerabilities (e.g. '../../etc/passwd').
        """
        if not object_key or not object_key.strip():
            raise ValueError("Object key cannot be empty")

        # Disallow leading directory separators or Windows drive root
        if object_key.startswith(("/", "\\")):
            raise ValueError("Path traversal detected: leading directory separator not permitted")

        # Strip null bytes
        clean_key = object_key.replace("\x00", "")

        # Resolve path
        target = (self.base_path / clean_key).resolve()

        # Strict boundary check against base directory
        try:
            target.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Path traversal detected for key: '{object_key}'")

        return target

    def save_file(
        self,
        object_key: str,
        content: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageItemInfo:
        target_path = self._resolve_safe_path(object_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = target_path.with_suffix(f"{target_path.suffix}.tmp_{os.getpid()}")
        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            with open(tmp_path, "wb") as f_out:
                while True:
                    chunk = content.read(64 * 1024)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    hasher.update(chunk)
                    total_bytes += len(chunk)

            # Atomic replace to prevent partial corrupted files
            tmp_path.replace(target_path)
        except Exception:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise

        checksum = hasher.hexdigest()
        relative_stored = str(target_path.relative_to(self.base_path)).replace("\\", "/")

        return StorageItemInfo(
            stored_path_or_key=relative_stored,
            object_key=object_key,
            size_bytes=total_bytes,
            sha256_checksum=checksum,
        )

    def get_file(self, object_key: str) -> BinaryIO:
        target_path = self._resolve_safe_path(object_key)
        if not target_path.is_file():
            raise FileNotFoundError(f"Object not found: '{object_key}'")
        return open(target_path, "rb")

    def delete_file(self, object_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(object_key)
        except ValueError:
            return False

        if target_path.is_file():
            target_path.unlink()
            return True
        return False

    def file_exists(self, object_key: str) -> bool:
        try:
            target_path = self._resolve_safe_path(object_key)
            return target_path.is_file()
        except ValueError:
            return False

    def get_storage_stats(self) -> StorageStatsInfo:
        total_files = 0
        total_bytes = 0

        if self.base_path.exists():
            for entry in self.base_path.rglob("*"):
                if entry.is_file() and not entry.name.endswith(".gitkeep") and not entry.name.endswith(".tmp"):
                    total_files += 1
                    try:
                        total_bytes += entry.stat().st_size
                    except OSError:
                        pass

        return StorageStatsInfo(
            provider_name="local",
            total_files=total_files,
            total_bytes=total_bytes,
            base_location=str(self.base_path),
        )
