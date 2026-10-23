"""Tests for S3CompatibleStorage adapter (MinIO / S3).

Skips live network tests when no local S3/MinIO service is reachable,
while testing key sanitization and driver initialization.
"""

from io import BytesIO
import os
import socket
from urllib.parse import urlparse
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
    import app.storage.s3 as s3_mod

    if not BOTO3_AVAILABLE:
        with pytest.raises(RuntimeError, match="boto3 is required"):
            S3CompatibleStorage()


def test_s3_driver_key_sanitization():
    """Verify object keys are safely sanitized against null bytes and leading slashes."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 is not installed")

    # Initialize driver with offline dummy credentials
    driver = S3CompatibleStorage(
        endpoint_url="http://127.0.0.1:9000",
        access_key="dummy_access",
        secret_key="dummy_secret",
        bucket_name="test-bucket",
    )

    clean = driver._sanitize_key("/leading/slash/file.bin")
    assert clean == "leading/slash/file.bin"

    with pytest.raises(ValueError, match="cannot be empty"):
        driver._sanitize_key("")

    with pytest.raises(ValueError, match="cannot be empty"):
        driver._sanitize_key("   ")


@pytest.mark.skipif(
    not is_s3_endpoint_available(os.getenv("S3_ENDPOINT_URL", "")),
    reason="Local S3/MinIO service is not reachable. Skipping live S3 integration test.",
)
def test_live_s3_storage_lifecycle():
    """Live integration test against local MinIO or S3 service if configured and online."""
    driver = S3CompatibleStorage()
    key = "integration_test/live_sample.txt"
    content = b"Live MinIO integration test payload"

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
