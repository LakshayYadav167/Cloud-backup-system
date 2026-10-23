"""Full end-to-end integration test against live Floci S3 emulator.

Tests upload, versioning, download, restore, snapshot, and deletion
through the FastAPI REST API when STORAGE_PROVIDER=s3.
Skipped automatically when Floci emulator is not running.
"""

from io import BytesIO
import os
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import get_db, init_db
from app.main import app
from app.storage.s3 import is_s3_endpoint_available


@pytest.mark.skipif(
    not is_s3_endpoint_available(os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:4566")),
    reason="Floci S3 emulator is not running on port 4566. Skipping Floci E2E test.",
)
def test_floci_e2e_full_lifecycle(client: TestClient, monkeypatch):
    """End-to-end workflow verifying S3/Floci integration across all endpoints."""
    # Configure backend to use S3/Floci
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "s3")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "http://127.0.0.1:4566")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY", "test")
    monkeypatch.setattr(settings, "S3_SECRET_KEY", "test")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "cloud-backup-system")

    # 1. Health check returns healthy with S3 provider
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
    assert health_res.json()["storage_provider"] == "s3"

    # 2. Upload file v1 to Floci
    v1_content = b"Floci end-to-end test document: Version 1"
    res1 = client.post(
        "/api/v1/files/upload",
        files={"file": ("floci_report.pdf", BytesIO(v1_content), "application/pdf")},
        data={"summary": "Initial draft stored in Floci"},
    )
    assert res1.status_code == 201
    file_id = res1.json()["file"]["id"]
    v1_id = res1.json()["version"]["id"]
    assert res1.json()["file"]["total_versions"] == 1

    # 3. Upload file v2 with same filename (immutable versioning)
    v2_content = b"Floci end-to-end test document: Version 2 updated"
    res2 = client.post(
        "/api/v1/files/upload",
        files={"file": ("floci_report.pdf", BytesIO(v2_content), "application/pdf")},
        data={"summary": "Revised draft stored in Floci"},
    )
    assert res2.status_code == 201
    v2_id = res2.json()["version"]["id"]
    assert res2.json()["file"]["id"] == file_id
    assert res2.json()["file"]["total_versions"] == 2
    assert res2.json()["version"]["version_number"] == 2

    # 4. Download current version (v2)
    dl_v2 = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_v2.status_code == 200
    assert dl_v2.content == v2_content

    # 5. Download historical version (v1)
    dl_v1 = client.get(f"/api/v1/files/{file_id}/download?version_id={v1_id}")
    assert dl_v1.status_code == 200
    assert dl_v1.content == v1_content

    # 6. Restore v1 as current version
    restore_res = client.post(f"/api/v1/files/{file_id}/restore/{v1_id}")
    assert restore_res.status_code == 200
    assert restore_res.json()["success"] is True
    assert restore_res.json()["file"]["current_version_id"] == v1_id
    assert restore_res.json()["file"]["current_version_number"] == 1

    # Verify download after restore returns v1 content
    dl_restored = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_restored.status_code == 200
    assert dl_restored.content == v1_content

    # 7. Create a system backup snapshot
    snapshot_res = client.post("/api/v1/backups/trigger?notes=Floci+E2E+Snapshot")
    assert snapshot_res.status_code == 201
    assert snapshot_res.json()["status"] == "COMPLETED"
    assert snapshot_res.json()["total_files"] >= 1

    # 8. Check storage stats reflects S3/Floci
    stats_res = client.get("/api/v1/storage/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["provider"] == "s3"
    assert stats_res.json()["total_files"] >= 1

    # 9. Delete file and all versions
    del_res = client.delete(f"/api/v1/files/{file_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 10. Verify file is no longer downloadable
    dl_after_del = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_after_del.status_code == 404
