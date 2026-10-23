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
