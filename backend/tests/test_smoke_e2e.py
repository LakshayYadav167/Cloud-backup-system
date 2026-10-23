"""End-to-End Smoke Test verifying the 10 core Cloud Backup System operations.

Validates the complete lifecycle:
1. Health check verification.
2. Initial test file upload.
3. Catalog listing and file download.
4. Content integrity verification via SHA-256.
5. Upload of a new version.
6. Historical version download.
7. Rollback / point-in-time version restoration.
8. Creation and listing of an immutable backup snapshot.
9. File deletion and physical storage cleanup.
10. Graceful failure when the selected storage provider is unavailable.
"""

from io import BytesIO
import hashlib
from fastapi.testclient import TestClient
from app.core.config import settings


def test_complete_end_to_end_smoke_lifecycle(client: TestClient, monkeypatch):
    """Execute complete 10-step smoke test sequence in an isolated test environment."""

    # --------------------------------------------------------------------------
    # Step 1: Health check
    # --------------------------------------------------------------------------
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["database_status"] == "connected"
    assert health_data["storage_provider"] == "local"

    # --------------------------------------------------------------------------
    # Step 2: Upload a test file (Version 1)
    # --------------------------------------------------------------------------
    v1_content = b"End-to-End Smoke Test: Baseline Version 1\nTimestamp: 2026-10-24\n"
    v1_hasher = hashlib.sha256(v1_content)
    v1_checksum = v1_hasher.hexdigest()

    upload_v1_res = client.post(
        "/api/v1/files/upload?change_summary=Initial+smoke+upload",
        files={"file": ("smoke_artifact.txt", BytesIO(v1_content), "text/plain")},
    )
    assert upload_v1_res.status_code == 201, f"V1 upload failed: {upload_v1_res.text}"
    v1_data = upload_v1_res.json()
    file_id = v1_data["file"]["id"]
    v1_version_id = v1_data["version"]["id"]
    assert v1_data["file"]["filename"] == "smoke_artifact.txt"
    assert v1_data["file"]["sha256"] == v1_checksum
    assert v1_data["file"]["current_version_number"] == 1

    # --------------------------------------------------------------------------
    # Step 3: List and download it
    # --------------------------------------------------------------------------
    list_res = client.get("/api/v1/files?search=smoke_artifact")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    matched_ids = [item["id"] for item in list_data["items"]]
    assert file_id in matched_ids

    download_v1_res = client.get(f"/api/v1/files/{file_id}/download")
    assert download_v1_res.status_code == 200

    # --------------------------------------------------------------------------
    # Step 4: Verify downloaded content
    # --------------------------------------------------------------------------
    assert download_v1_res.content == v1_content
    assert hashlib.sha256(download_v1_res.content).hexdigest() == v1_checksum
    assert "smoke_artifact.txt" in download_v1_res.headers.get("Content-Disposition", "")

    # --------------------------------------------------------------------------
    # Step 5: Upload a second version (Version 2)
    # --------------------------------------------------------------------------
    v2_content = b"End-to-End Smoke Test: Updated Version 2 with revised configuration\n"
    v2_checksum = hashlib.sha256(v2_content).hexdigest()

    upload_v2_res = client.post(
        "/api/v1/files/upload?change_summary=Second+smoke+version",
        files={"file": ("smoke_artifact.txt", BytesIO(v2_content), "text/plain")},
    )
    assert upload_v2_res.status_code == 201
    v2_data = upload_v2_res.json()
    assert v2_data["file"]["id"] == file_id
    assert v2_data["file"]["current_version_number"] == 2
    assert v2_data["file"]["total_versions"] == 2
    assert v2_data["file"]["sha256"] == v2_checksum
    v2_version_id = v2_data["version"]["id"]

    # --------------------------------------------------------------------------
    # Step 6: Download the historical version (Version 1)
    # --------------------------------------------------------------------------
    # Default download should now serve Version 2
    dl_current = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_current.status_code == 200
    assert dl_current.content == v2_content

    # Explicit version download must serve Version 1
    dl_historical = client.get(f"/api/v1/files/{file_id}/download?version_id={v1_version_id}")
    assert dl_historical.status_code == 200
    assert dl_historical.content == v1_content
    assert hashlib.sha256(dl_historical.content).hexdigest() == v1_checksum

    # --------------------------------------------------------------------------
    # Step 7: Restore the earlier version (Rollback to Version 1)
    # --------------------------------------------------------------------------
    restore_res = client.post(f"/api/v1/files/{file_id}/restore/{v1_version_id}")
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["success"] is True
    assert restore_data["file"]["current_version_id"] == v1_version_id
    assert restore_data["file"]["current_version_number"] == 1

    # Default download must now serve Version 1 content
    dl_after_restore = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_after_restore.status_code == 200
    assert dl_after_restore.content == v1_content

    # --------------------------------------------------------------------------
    # Step 8: Create and list a backup snapshot
    # --------------------------------------------------------------------------
    trigger_res = client.post("/api/v1/backups/trigger?notes=Smoke+E2E+Snapshot")
    assert trigger_res.status_code == 201
    snapshot_data = trigger_res.json()
    assert snapshot_data["status"] == "COMPLETED"
    assert snapshot_data["total_files"] >= 1
    assert snapshot_data["notes"] == "Smoke E2E Snapshot"
    assert len(snapshot_data["checksum"]) == 64

    # List backup history
    history_res = client.get("/api/v1/backups/history")
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["total"] >= 1
    assert any(s["id"] == snapshot_data["id"] for s in history_data["snapshots"])

    # --------------------------------------------------------------------------
    # Step 9: Delete the test file
    # --------------------------------------------------------------------------
    delete_res = client.delete(f"/api/v1/files/{file_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True

    # Confirm file no longer appears in file listing
    post_delete_list = client.get(f"/api/v1/files?search=smoke_artifact")
    assert post_delete_list.status_code == 200
    assert post_delete_list.json()["total"] == 0

    # Confirm download returns 404
    post_delete_dl = client.get(f"/api/v1/files/{file_id}/download")
    assert post_delete_dl.status_code == 404

    # --------------------------------------------------------------------------
    # Step 10: Confirm graceful failure when selected storage provider is unavailable
    # --------------------------------------------------------------------------
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "s3")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "http://127.0.0.1:59999")

    # Uploading when S3 is unavailable must fail with 500 and not silently write to local disk
    fail_upload_res = client.post(
        "/api/v1/files/upload",
        files={"file": ("unreachable_smoke.txt", BytesIO(b"Data"), "text/plain")},
    )
    assert fail_upload_res.status_code == 500
    assert "storage provider failed" in fail_upload_res.json()["detail"].lower()

    # Health endpoint reports degraded status when S3 is unreachable
    degraded_health = client.get("/api/v1/health")
    assert degraded_health.status_code == 200
    assert degraded_health.json()["status"] == "degraded"
    assert degraded_health.json()["storage_status"] == "unavailable"
