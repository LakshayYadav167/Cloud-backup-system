"""Integration tests for point-in-time backup snapshots and audit history."""

from io import BytesIO
from fastapi.testclient import TestClient


def test_trigger_backup_snapshot(client: TestClient):
    """Triggering a backup snapshot must record all active file versions and manifest hash."""
    # Upload 2 files
    client.post(
        "/api/v1/files/upload",
        files={"file": ("file_a.txt", BytesIO(b"Data in File A"), "text/plain")},
    )
    client.post(
        "/api/v1/files/upload",
        files={"file": ("file_b.json", BytesIO(b'{"key": "value"}'), "application/json")},
    )

    # Trigger backup
    trigger_res = client.post("/api/v1/backups/trigger?notes=Weekly+scheduled+backup")
    assert trigger_res.status_code == 201
    data = trigger_res.json()

    assert data["status"] == "COMPLETED"
    assert data["total_files"] == 2
    assert data["total_bytes"] == len(b"Data in File A") + len(b'{"key": "value"}')
    assert len(data["checksum"]) == 64
    assert data["notes"] == "Weekly scheduled backup"


def test_list_backup_history(client: TestClient):
    """Backup history must return chronological snapshots."""
    # Trigger 2 backups
    client.post("/api/v1/backups/trigger?notes=Snapshot+One")
    client.post("/api/v1/backups/trigger?notes=Snapshot+Two")

    history_res = client.get("/api/v1/backups/history")
    assert history_res.status_code == 200
    data = history_res.json()

    assert data["total"] >= 2
    assert len(data["snapshots"]) >= 2
    notes = [s["notes"] for s in data["snapshots"]]
    assert "Snapshot Two" in notes
    assert "Snapshot One" in notes


def test_snapshot_manifest_integrity_and_checksum(client: TestClient):
    """Manifest checksum must be deterministic SHA-256 of sorted file_id:sha256 pairs."""
    import hashlib

    res_a = client.post(
        "/api/v1/files/upload",
        files={"file": ("alpha.txt", BytesIO(b"Alpha Payload"), "text/plain")},
    )
    res_b = client.post(
        "/api/v1/files/upload",
        files={"file": ("beta.txt", BytesIO(b"Beta Payload"), "text/plain")},
    )
    assert res_a.status_code == 201
    assert res_b.status_code == 201

    file_a = res_a.json()["file"]
    file_b = res_b.json()["file"]

    # Compute expected manifest checksum
    items = sorted(
        [(file_a["id"], file_a["sha256"]), (file_b["id"], file_b["sha256"])],
        key=lambda x: x[0],
    )
    hasher = hashlib.sha256()
    for f_id, f_hash in items:
        hasher.update(f"{f_id}:{f_hash}\n".encode("utf-8"))
    expected_checksum = hasher.hexdigest()

    trigger_res = client.post("/api/v1/backups/trigger?notes=Integrity+verification")
    assert trigger_res.status_code == 201
    snapshot = trigger_res.json()
    assert snapshot["checksum"] == expected_checksum
    assert snapshot["total_files"] == 2


def test_empty_snapshot_creation(client: TestClient):
    """Triggering a snapshot with zero files creates a valid empty snapshot."""
    import hashlib

    trigger_res = client.post("/api/v1/backups/trigger?notes=Empty+system+snapshot")
    assert trigger_res.status_code == 201
    snapshot = trigger_res.json()

    assert snapshot["status"] == "COMPLETED"
    assert snapshot["total_files"] == 0
    assert snapshot["total_bytes"] == 0
    # Empty string hashed
    assert snapshot["checksum"] == hashlib.sha256(b"").hexdigest()


def test_snapshot_excludes_deleted_files(client: TestClient):
    """Deleted files must be excluded from subsequent backup snapshots."""
    res1 = client.post(
        "/api/v1/files/upload",
        files={"file": ("keep.txt", BytesIO(b"Keep me"), "text/plain")},
    )
    res2 = client.post(
        "/api/v1/files/upload",
        files={"file": ("delete_me.txt", BytesIO(b"Discard"), "text/plain")},
    )
    del_id = res2.json()["file"]["id"]

    # Delete second file
    del_res = client.delete(f"/api/v1/files/{del_id}")
    assert del_res.status_code == 200

    trigger_res = client.post("/api/v1/backups/trigger?notes=Excluding+deleted")
    assert trigger_res.status_code == 201
    snapshot = trigger_res.json()
    assert snapshot["total_files"] == 1
    assert snapshot["total_bytes"] == len(b"Keep me")


def test_missing_physical_storage_object_returns_404(client: TestClient):
    """If the underlying physical object is deleted from storage, download returns clean 404."""
    import os
    from pathlib import Path
    from app.core.config import settings

    upload_res = client.post(
        "/api/v1/files/upload",
        files={"file": ("lost_file.txt", BytesIO(b"Temporary on disk"), "text/plain")},
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["file"]["id"]

    # Delete all files in the temporary storage directory to simulate missing object
    storage_path = Path(settings.LOCAL_STORAGE_PATH)
    for p in storage_path.glob("**/*"):
        if p.is_file():
            os.remove(p)

    # Attempt download - should fail cleanly with 404 rather than 500
    dl_res = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_res.status_code == 404
    assert "not found on storage backend" in dl_res.json()["detail"].lower()
