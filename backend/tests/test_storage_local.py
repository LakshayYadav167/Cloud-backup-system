"""Unit tests for the LocalFileSystemStorage provider adapter."""

from io import BytesIO
import pytest

from app.storage.local import LocalFileSystemStorage


def test_save_and_retrieve_file(local_storage: LocalFileSystemStorage):
    """Verify storing and retrieving content accurately preserves data and checksum."""
    data = b"Hello, Cloud Backup System local storage verification!"
    key = "documents/test_file.txt"

    item_info = local_storage.save_file(key, BytesIO(data))
    assert item_info.size_bytes == len(data)
    assert len(item_info.sha256_checksum) == 64
    assert local_storage.file_exists(key) is True

    # Retrieve stream
    stream = local_storage.get_file(key)
    retrieved_data = stream.read()
    stream.close()

    assert retrieved_data == data


def test_delete_file(local_storage: LocalFileSystemStorage):
    """Verify deleting a file removes it from disk and reports existence correctly."""
    key = "temp/to_delete.bin"
    local_storage.save_file(key, BytesIO(b"transient data"))
    assert local_storage.file_exists(key) is True

    deleted = local_storage.delete_file(key)
    assert deleted is True
    assert local_storage.file_exists(key) is False

    # Second delete returns False
    assert local_storage.delete_file(key) is False


def test_get_nonexistent_file_raises_error(local_storage: LocalFileSystemStorage):
    """Attempting to get a non-existent file must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        local_storage.get_file("non_existent_key_12345.dat")


def test_path_traversal_prevention(local_storage: LocalFileSystemStorage):
    """Attempting path traversal must raise ValueError and be blocked."""
    dangerous_keys = [
        "../outside.txt",
        "../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "/absolute/escape.txt",
        "nested/../../escape.txt",
    ]

    for key in dangerous_keys:
        with pytest.raises(ValueError, match="Path traversal|empty"):
            local_storage.save_file(key, BytesIO(b"malicious"))

        with pytest.raises(ValueError, match="Path traversal|empty"):
            local_storage.get_file(key)

        assert local_storage.file_exists(key) is False
        assert local_storage.delete_file(key) is False


def test_storage_stats_calculation(local_storage: LocalFileSystemStorage):
    """Verify that storage statistics aggregate counts and bytes accurately."""
    local_storage.save_file("file1.bin", BytesIO(b"12345"))  # 5 bytes
    local_storage.save_file("sub/file2.bin", BytesIO(b"1234567890"))  # 10 bytes

    stats = local_storage.get_storage_stats()
    assert stats.provider_name == "local"
    assert stats.total_files == 2
    assert stats.total_bytes == 15
