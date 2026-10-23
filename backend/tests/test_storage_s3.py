"""Tests for S3CompatibleStorage adapter (Floci / S3).

Includes fast mocked unit tests for CI/offline environments,
and live integration tests against local Floci emulator when online.
Never connects to real AWS or external cloud endpoints.
"""

from io import BytesIO
import os
import socket
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
from botocore.exceptions import ClientError, EndpointConnectionError
import pytest

from app.core.config import settings
from app.storage.s3 import S3CompatibleStorage, BOTO3_AVAILABLE


def is_s3_endpoint_available(endpoint_url: str) -> bool:
    """Check if the given HTTP/S3 endpoint is listening on its port."""
    if not endpoint_url:
        return False
    try:
        parsed = urlparse(endpoint_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def test_s3_driver_initialization_requires_boto3(monkeypatch):
    """Driver should raise RuntimeError if boto3 is missing."""
    if not BOTO3_AVAILABLE:
        with pytest.raises(RuntimeError, match="boto3 is required"):
            S3CompatibleStorage()


def test_s3_driver_key_sanitization():
    """Verify object keys are safely sanitized against null bytes and leading slashes."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 is not installed")

    driver = S3CompatibleStorage(
        endpoint_url="http://127.0.0.1:4566",
        access_key="test",
        secret_key="test",
        bucket_name="test-bucket",
        auto_create_bucket=False,
    )

    clean = driver._sanitize_key("/leading/slash/file.bin")
    assert clean == "leading/slash/file.bin"

    clean_null = driver._sanitize_key("/path/with/\x00null.txt")
    assert clean_null == "path/with/null.txt"

    with pytest.raises(ValueError, match="cannot be empty"):
        driver._sanitize_key("")

    with pytest.raises(ValueError, match="cannot be empty"):
        driver._sanitize_key("   ")


def test_s3_driver_floci_defaults():
    """Verify default configurations point to harmless local Floci emulator settings."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 is not installed")

    driver = S3CompatibleStorage(auto_create_bucket=False)
    assert "4566" in driver.endpoint_url or "localhost" in driver.endpoint_url or "127.0.0.1" in driver.endpoint_url
    assert driver.access_key == "test"
    assert driver.secret_key == "test"
    assert driver.bucket_name == "cloud-backup-system"
    assert driver.region == "us-east-1"


def test_s3_driver_is_available_when_offline():
    """When pointing to an offline port, is_available returns False gracefully."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 is not installed")

    driver = S3CompatibleStorage(
        endpoint_url="http://127.0.0.1:59999",  # unused port
        auto_create_bucket=False,
    )
    assert driver.is_available() is False


def test_s3_driver_mocked_lifecycle():
    """Unit test for S3 storage adapter using mocked boto3 client (₹0 cost, zero network)."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 is not installed")

    driver = S3CompatibleStorage(
        endpoint_url="http://127.0.0.1:4566",
        access_key="test",
        secret_key="test",
        bucket_name="mock-bucket",
        auto_create_bucket=False,
    )

    mock_client = MagicMock()
    driver.client = mock_client

    # 1. save_file
    payload = b"Mock S3 file payload for unit testing"
    key = "files/test_file.txt"
    info = driver.save_file(key, BytesIO(payload), metadata={"filename": "test.txt"})
    assert info.object_key == key
    assert info.size_bytes == len(payload)
    mock_client.upload_fileobj.assert_called_once()

    # 2. file_exists - True
    mock_client.head_object.return_value = {"ContentLength": len(payload)}
    assert driver.file_exists(key) is True

    # 3. file_exists - False (404)
    mock_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )
    assert driver.file_exists("nonexistent.txt") is False

    # 4. get_file - Success
    body_mock = MagicMock()
    body_mock.read.return_value = payload
    mock_client.get_object.return_value = {"Body": body_mock}
    stream = driver.get_file(key)
    assert stream.read() == payload

    # 5. get_file - Not Found
    mock_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
        "GetObject",
    )
    with pytest.raises(FileNotFoundError, match="Object not found in S3 bucket"):
        driver.get_file("missing.txt")

    # 6. delete_file
    mock_client.delete_object.return_value = {}
    assert driver.delete_file(key) is True
    mock_client.delete_object.assert_called_with(Bucket="mock-bucket", Key=key)

    # 7. get_storage_stats
    paginator_mock = MagicMock()
    paginator_mock.paginate.return_value = [
        {"Contents": [{"Key": "k1", "Size": 100}, {"Key": "k2", "Size": 250}]}
    ]
    mock_client.get_paginator.return_value = paginator_mock

    stats = driver.get_storage_stats()
    assert stats.provider_name == "s3"
    assert stats.total_files == 2
    assert stats.total_bytes == 350
    assert "mock-bucket" in stats.base_location


@pytest.mark.skipif(
    not is_s3_endpoint_available(os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:4566")),
    reason="Local Floci emulator is not running on port 4566. Skipping live integration test.",
)
def test_live_floci_storage_lifecycle():
    """Live integration test against local Floci emulator service when online."""
    driver = S3CompatibleStorage(
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:4566"),
        access_key="test",
        secret_key="test",
        bucket_name="cloud-backup-system-test",
    )
    key = "integration_test/live_sample.txt"
    content = b"Live Floci integration test payload"

    # Save
    info = driver.save_file(key, BytesIO(content))
    assert info.size_bytes == len(content)

    # Exists
    assert driver.file_exists(key) is True

    # Get
    stream = driver.get_file(key)
    assert stream.read() == content

    # Delete
    assert driver.delete_file(key) is True
    assert driver.file_exists(key) is False
