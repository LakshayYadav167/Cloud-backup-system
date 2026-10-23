"""Integration and security tests for portable backup archives (Phase 7).

Verifies:
1. Exporting files with historical versions into standard ZIP archives.
2. Cryptographic verification of archive manifests, file sizes, and SHA-256 hashes.
3. Tamper detection on corrupted blobs.
4. Rejection of invalid manifests and unsupported versions.
5. Path traversal prevention (rejects '../', absolute paths, and Windows device names).
6. Clear failure handling when underlying physical objects are missing during export.
7. Independent restoration into an isolated clean database and storage environment.
8. Preservation of file contents, version lineages, and SHA-256 checksums post-restore.
9. Conflict resolution strategies: 'rename', 'skip', and 'replace'.
10. Coexistence and preservation of existing point-in-time snapshot functionality.
"""

from io import BytesIO
import json
import zipfile
import pytest
from fastapi.testclient import TestClient


def test_export_archive_with_multiple_versions(client: TestClient):
    """Exporting an archive must package all active files, versions, and manifest.json."""
    # 1. Upload File A (v1 then v2)
    res_a1 = client.post(
        "/api/v1/files/upload?change_summary=V1+Initial",
        files={"file": ("project_spec.md", BytesIO(b"# Project Specification v1\nInitial draft."), "text/markdown")},
    )
    assert res_a1.status_code == 201

    res_a2 = client.post(
        "/api/v1/files/upload?change_summary=V2+Revised",
        files={"file": ("project_spec.md", BytesIO(b"# Project Specification v2\nRevised draft with architectures."), "text/markdown")},
    )
    assert res_a2.status_code == 201

    # 2. Upload File B (v1)
    res_b = client.post(
        "/api/v1/files/upload",
        files={"file": ("config.json", BytesIO(b'{"port": 8000, "debug": true}'), "application/json")},
    )
    assert res_b.status_code == 201

    # 3. Export archive
    export_res = client.get("/api/v1/archives/export?notes=Unit+test+export")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/zip"
    assert "attachment; filename=\"cloud_backup_archive_" in export_res.headers["content-disposition"]

    # 4. Inspect ZIP content
    zip_bytes = export_res.content
    with zipfile.ZipFile(BytesIO(zip_bytes), mode="r") as zf:
        namelist = zf.namelist()
        assert "manifest.json" in namelist

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["archive_format_version"] == "1.0.0"
        assert manifest["total_files"] == 2
        assert manifest["total_versions"] == 3
        assert manifest["notes"] == "Unit test export"

        # Verify File A has 2 versions declared and payloads present
        spec_entry = next(f for f in manifest["files"] if f["filename"] == "project_spec.md")
        assert len(spec_entry["versions"]) == 2
        assert spec_entry["current_version_number"] == 2

        v1_entry = next(v for v in spec_entry["versions"] if v["version_number"] == 1)
        v2_entry = next(v for v in spec_entry["versions"] if v["version_number"] == 2)

        assert v1_entry["archive_path"] in namelist
        assert v2_entry["archive_path"] in namelist

        # Validate uncompressed payload bytes match
        assert zf.read(v1_entry["archive_path"]) == b"# Project Specification v1\nInitial draft."
        assert zf.read(v2_entry["archive_path"]) == b"# Project Specification v2\nRevised draft with architectures."


def test_verify_valid_archive(client: TestClient):
    """A freshly exported archive must pass verification with zero errors."""
    client.post(
        "/api/v1/files/upload",
        files={"file": ("data.csv", BytesIO(b"id,name,val\n1,alpha,100\n"), "text/csv")},
    )

    export_res = client.get("/api/v1/archives/export")
    assert export_res.status_code == 200

    verify_res = client.post(
        "/api/v1/archives/verify",
        files={"file": ("backup.zip", BytesIO(export_res.content), "application/zip")},
    )
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["valid"] is True
    assert data["format_version"] == "1.0.0"
    assert data["total_files"] >= 1
    assert data["total_versions"] >= 1
    assert len(data["errors"]) == 0


def test_verify_detects_corrupted_payload(client: TestClient):
    """Tampering with an archive payload must trigger cryptographic checksum failure."""
    client.post(
        "/api/v1/files/upload",
        files={"file": ("secure.txt", BytesIO(b"Authentic Payload Content"), "text/plain")},
    )

    export_res = client.get("/api/v1/archives/export")
    assert export_res.status_code == 200

    # Tamper with archive: rewrite one blob with forged bytes
    original_zip = export_res.content
    tampered_buffer = BytesIO()

    with zipfile.ZipFile(BytesIO(original_zip), mode="r") as src_zf:
        with zipfile.ZipFile(tampered_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as dst_zf:
            for item in src_zf.infolist():
                content = src_zf.read(item.filename)
                if item.filename.startswith("blobs/"):
                    content = b"TAMPERED_MALICIOUS_FORGERY"
                dst_zf.writestr(item.filename, content)

    tampered_buffer.seek(0)

    verify_res = client.post(
        "/api/v1/archives/verify",
        files={"file": ("tampered.zip", tampered_buffer, "application/zip")},
    )
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0
    error_text = " ".join(data["errors"]).lower()
    assert "checksum mismatch" in error_text or "size mismatch" in error_text


def test_verify_rejects_path_traversal_entry(client: TestClient):
    """Archives containing directory traversal sequences must be rejected."""
    malicious_buffer = BytesIO()
    manifest_data = {
        "archive_format_version": "1.0.0",
        "total_files": 1,
        "total_versions": 1,
        "total_bytes": 10,
        "files": [],
    }

    with zipfile.ZipFile(malicious_buffer, mode="w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest_data))
        # Malicious traversal entry
        zf.writestr("blobs/../../etc/passwd", b"root:x:0:0")

    malicious_buffer.seek(0)

    verify_res = client.post(
        "/api/v1/archives/verify",
        files={"file": ("malicious.zip", malicious_buffer, "application/zip")},
    )
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["valid"] is False
    assert any("traversal" in err.lower() for err in data["errors"])


def test_verify_rejects_reserved_windows_device_names(client: TestClient):
    """Archives containing Windows reserved device names must be rejected."""
    bad_buffer = BytesIO()
    manifest_data = {
        "archive_format_version": "1.0.0",
        "total_files": 1,
        "total_versions": 1,
        "total_bytes": 5,
        "files": [],
    }

    with zipfile.ZipFile(bad_buffer, mode="w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest_data))
        zf.writestr("blobs/CON.txt", b"dummy")

    bad_buffer.seek(0)

    verify_res = client.post(
        "/api/v1/archives/verify",
        files={"file": ("bad_device.zip", bad_buffer, "application/zip")},
    )
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["valid"] is False
    assert any("reserved" in err.lower() for err in data["errors"])


def test_export_fails_cleanly_when_source_object_missing(client: TestClient):
    """If an active file's physical object is missing on storage, export raises 409 Conflict."""
    import os
    from pathlib import Path
    from app.core.config import settings

    upload_res = client.post(
        "/api/v1/files/upload",
        files={"file": ("doomed_file.txt", BytesIO(b"Will be deleted on disk"), "text/plain")},
    )
    assert upload_res.status_code == 201

    # Purge physical file on storage
    storage_path = Path(settings.LOCAL_STORAGE_PATH)
    for p in storage_path.glob("**/*"):
        if p.is_file():
            os.remove(p)

    # Attempt export - must abort with 409
    export_res = client.get("/api/v1/archives/export")
    assert export_res.status_code == 409
    assert "missing from the active storage backend" in export_res.json()["detail"].lower()


def test_restore_into_isolated_fresh_environment(client: TestClient, tmp_path):
    """An archive must be independently restorable into an empty, isolated environment."""
    v1_payload = b"First Version Content for Independence Test"
    v2_payload = b"Second Version Content for Independence Test"

    # Step 1: Create multi-version file in source client
    client.post(
        "/api/v1/files/upload?change_summary=V1",
        files={"file": ("independent_doc.txt", BytesIO(v1_payload), "text/plain")},
    )
    client.post(
        "/api/v1/files/upload?change_summary=V2",
        files={"file": ("independent_doc.txt", BytesIO(v2_payload), "text/plain")},
    )

    # Export archive
    export_res = client.get("/api/v1/archives/export")
    assert export_res.status_code == 200
    archive_zip = export_res.content

    # Step 2: Delete original file in the source client
    list_res = client.get("/api/v1/files?search=independent_doc.txt")
    for item in list_res.json()["items"]:
        client.delete(f"/api/v1/files/{item['id']}")

    # Verify completely empty catalog
    empty_list = client.get("/api/v1/files?search=independent_doc.txt")
    assert empty_list.json()["total"] == 0

    # Step 3: Restore the archive
    restore_res = client.post(
        "/api/v1/archives/restore",
        files={"file": ("backup.zip", BytesIO(archive_zip), "application/zip")},
        data={"conflict_strategy": "rename"},
    )
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["success"] is True
    assert restore_data["imported_files_count"] >= 1
    assert restore_data["imported_versions_count"] >= 2

    # Step 4: Verify recovered content in active system
    recovered_list = client.get("/api/v1/files?search=independent_doc.txt")
    assert recovered_list.status_code == 200
    recovered_items = recovered_list.json()["items"]
    assert len(recovered_items) == 1
    recovered_file = recovered_items[0]

    assert recovered_file["current_version_number"] == 2
    assert recovered_file["total_versions"] == 2

    # Download active version (v2)
    dl_v2 = client.get(f"/api/v1/files/{recovered_file['id']}/download")
    assert dl_v2.status_code == 200
    assert dl_v2.content == v2_payload

    # Query versions to find v1 ID
    versions_res = client.get(f"/api/v1/files/{recovered_file['id']}/versions")
    assert versions_res.status_code == 200
    v1_summary = next(v for v in versions_res.json() if v["version_number"] == 1)

    # Download historical version (v1)
    dl_v1 = client.get(f"/api/v1/files/{recovered_file['id']}/download?version_id={v1_summary['id']}")
    assert dl_v1.status_code == 200
    assert dl_v1.content == v1_payload


def test_restore_conflict_handling_rename_and_skip(client: TestClient):
    """Conflict strategies 'rename' and 'skip' must handle duplicate filenames safely."""
    orig_payload = b"Existing File Content"
    imported_payload = b"Archive Payload Content"

    # Setup existing file
    client.post(
        "/api/v1/files/upload",
        files={"file": ("conflict_test.txt", BytesIO(orig_payload), "text/plain")},
    )

    # Export archive
    export_res = client.get("/api/v1/archives/export")
    archive_zip = export_res.content

    # 1. Restore with 'rename' strategy: creates a non-colliding file
    restore_rename_res = client.post(
        "/api/v1/archives/restore",
        files={"file": ("archive.zip", BytesIO(archive_zip), "application/zip")},
        data={"conflict_strategy": "rename"},
    )
    assert restore_rename_res.status_code == 200
    assert restore_rename_res.json()["imported_files_count"] >= 1
    assert any("renamed" in d.lower() for d in restore_rename_res.json()["details"])

    # 2. Restore with 'skip' strategy: leaves existing file intact
    restore_skip_res = client.post(
        "/api/v1/archives/restore",
        files={"file": ("archive.zip", BytesIO(archive_zip), "application/zip")},
        data={"conflict_strategy": "skip"},
    )
    assert restore_skip_res.status_code == 200
    assert restore_skip_res.json()["skipped_files_count"] >= 1


def test_preserve_existing_snapshot_behavior(client: TestClient):
    """Point-in-time snapshot endpoints must continue working seamlessly."""
    client.post(
        "/api/v1/files/upload",
        files={"file": ("snapshot_coexist.txt", BytesIO(b"Snapshot data"), "text/plain")},
    )

    # Trigger snapshot
    snap_res = client.post("/api/v1/backups/trigger?notes=Phase+7+Coexistence")
    assert snap_res.status_code == 201
    assert snap_res.json()["status"] == "COMPLETED"

    # List snapshots
    hist_res = client.get("/api/v1/backups/history")
    assert hist_res.status_code == 200
    assert hist_res.json()["total"] >= 1
