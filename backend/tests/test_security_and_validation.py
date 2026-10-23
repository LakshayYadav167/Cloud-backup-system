"""Tests verifying security restrictions, input sanitization, and error handling."""

from io import BytesIO
from fastapi.testclient import TestClient
from app.core.config import settings


def test_empty_filename_rejected(client: TestClient):
    """Uploading with an empty or whitespace filename must be rejected with 400 or 422."""
    # Whitespace filename rejected by our domain sanitizer with 400
    res1 = client.post(
        "/api/v1/files/upload",
        files={"file": ("   ", BytesIO(b"data"), "text/plain")},
    )
    assert res1.status_code == 400
    assert "empty" in res1.json()["detail"].lower()

    # Empty string filename rejected by form parser / sanitizer
    res2 = client.post(
        "/api/v1/files/upload",
        files={"file": ("", BytesIO(b"data"), "text/plain")},
    )
    assert res2.status_code in (400, 422)


def test_reserved_windows_device_names_rejected(client: TestClient):
    """Filenames matching Windows reserved names (CON, NUL, AUX, PRN) must be rejected."""
    forbidden = ["CON.txt", "prn.log", "aux.csv", "NUL", "com1.bin", "LPT2.dat"]

    for name in forbidden:
        res = client.post(
            "/api/v1/files/upload",
            files={"file": (name, BytesIO(b"content"), "text/plain")},
        )
        assert res.status_code == 400
        assert "reserved" in res.json()["detail"].lower()


def test_path_traversal_in_filename_sanitized(client: TestClient):
    """Directory components in uploaded filename must be stripped to base name only."""
    res = client.post(
        "/api/v1/files/upload",
        files={"file": ("../../../../etc/passwd", BytesIO(b"root:x:0:0"), "text/plain")},
    )
    assert res.status_code == 201
    # Original directory traversal is stripped, only base name stored
    assert res.json()["file"]["filename"] == "passwd"


def test_oversized_upload_rejected(client: TestClient, monkeypatch):
    """Files exceeding MAX_UPLOAD_SIZE_MB must be rejected with 413 Payload Too Large."""
    # Temporarily set max size to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    # Generate 1.2 MB data
    large_data = b"X" * (1024 * 1024 + 200 * 1024)

    res = client.post(
        "/api/v1/files/upload",
        files={"file": ("large_file.iso", BytesIO(large_data), "application/octet-stream")},
    )
    assert res.status_code == 413
    assert "exceeds" in res.json()["detail"].lower()


def test_restore_nonexistent_version_returns_404(client: TestClient):
    """Attempting to restore an invalid version ID must return 404."""
    upload_res = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.txt", BytesIO(b"hello"), "text/plain")},
    )
    file_id = upload_res.json()["file"]["id"]

    res = client.post(f"/api/v1/files/{file_id}/restore/non-existent-version-uuid")
    assert res.status_code == 404


def test_storage_stats_masks_absolute_paths(client: TestClient):
    """Storage statistics must not leak internal host directory paths in responses."""
    res = client.get("/api/v1/storage/stats")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "total_bytes" in data
    assert "quota_bytes" in data
    # Location should be relative/masked
    assert not data["base_location"].startswith("C:\\")
