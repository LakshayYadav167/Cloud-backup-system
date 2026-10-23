"""Integration tests for file upload, versioning, download, restore, and deletion."""

from io import BytesIO
from fastapi.testclient import TestClient


def test_upload_new_file(client: TestClient):
    """Uploading a new file must register metadata, create version 1, and return 201."""
    content = b"Content of sample project report."
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("project_report.txt", BytesIO(content), "text/plain")},
        data={"summary": "Initial draft of report"},
    )
    assert response.status_code == 201
    data = response.json()

    assert data["file"]["filename"] == "project_report.txt"
    assert data["file"]["total_versions"] == 1
    assert data["file"]["current_version_number"] == 1
    assert data["file"]["size_bytes"] == len(content)
    assert len(data["file"]["sha256"]) == 64
    assert data["version"]["version_number"] == 1
    assert data["version"]["change_summary"] == "Initial draft of report"


def test_upload_duplicate_filename_creates_new_version(client: TestClient):
    """Uploading a file with the same filename must preserve version 1 and create version 2."""
    v1_content = b"Version 1 content"
    v2_content = b"Version 2 updated content with new sections"

    # Upload v1
    res1 = client.post(
        "/api/v1/files/upload",
        files={"file": ("doc.txt", BytesIO(v1_content), "text/plain")},
        data={"summary": "First version"},
    )
    assert res1.status_code == 201
    file_id = res1.json()["file"]["id"]
    v1_id = res1.json()["version"]["id"]

    # Upload v2 with same filename
    res2 = client.post(
        "/api/v1/files/upload",
        files={"file": ("doc.txt", BytesIO(v2_content), "text/plain")},
        data={"summary": "Second version"},
    )
    assert res2.status_code == 201
    data2 = res2.json()

    # Same logical file ID
    assert data2["file"]["id"] == file_id
    assert data2["file"]["current_version_number"] == 2
    assert data2["file"]["total_versions"] == 2
    assert data2["file"]["size_bytes"] == len(v2_content)
    assert data2["version"]["version_number"] == 2
    v2_id = data2["version"]["id"]
    assert v1_id != v2_id

    # Verify both versions exist in version history
    versions_res = client.get(f"/api/v1/files/{file_id}/versions")
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[0]["is_current"] is True
    assert versions[1]["version_number"] == 1
    assert versions[1]["is_current"] is False


def test_download_current_and_historical_versions(client: TestClient):
    """Verify downloading serves current version by default, or historical version by ID."""
    v1_bytes = b"Initial database design notes."
    v2_bytes = b"Revised database design with sharding notes."

    res1 = client.post(
        "/api/v1/files/upload",
        files={"file": ("notes.txt", BytesIO(v1_bytes), "text/plain")},
    )
    file_id = res1.json()["file"]["id"]
    v1_id = res1.json()["version"]["id"]

    res2 = client.post(
        "/api/v1/files/upload",
        files={"file": ("notes.txt", BytesIO(v2_bytes), "text/plain")},
    )
    v2_id = res2.json()["version"]["id"]

    # Download default (should be v2)
    dl_default = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_default.status_code == 200
    assert dl_default.content == v2_bytes
    assert "Content-Disposition" in dl_default.headers
    assert "notes.txt" in dl_default.headers["Content-Disposition"]

    # Download specifically v1
    dl_v1 = client.get(f"/api/v1/files/{file_id}/download?version_id={v1_id}")
    assert dl_v1.status_code == 200
    assert dl_v1.content == v1_bytes


def test_restore_previous_version(client: TestClient):
    """Restoring a previous version must update current pointer while keeping history intact."""
    v1_data = b"Original baseline configuration"
    v2_data = b"Corrupted or broken configuration change"

    res1 = client.post(
        "/api/v1/files/upload",
        files={"file": ("config.yaml", BytesIO(v1_data), "application/x-yaml")},
    )
    file_id = res1.json()["file"]["id"]
    v1_id = res1.json()["version"]["id"]

    client.post(
        "/api/v1/files/upload",
        files={"file": ("config.yaml", BytesIO(v2_data), "application/x-yaml")},
    )

    # Restore to v1
    restore_res = client.post(f"/api/v1/files/{file_id}/restore/{v1_id}")
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["success"] is True
    assert restore_data["file"]["current_version_id"] == v1_id
    assert restore_data["file"]["current_version_number"] == 1

    # Now download default - must serve v1 content
    dl_res = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.content == v1_data


def test_list_and_search_files(client: TestClient):
    """Verify list endpoint supports search filtering and pagination."""
    client.post(
        "/api/v1/files/upload",
        files={"file": ("alpha_report.pdf", BytesIO(b"alpha"), "application/pdf")},
    )
    client.post(
        "/api/v1/files/upload",
        files={"file": ("beta_data.csv", BytesIO(b"beta"), "text/csv")},
    )
    client.post(
        "/api/v1/files/upload",
        files={"file": ("gamma_report.docx", BytesIO(b"gamma"), "application/vnd.ms-word")},
    )

    # Search for "report"
    search_res = client.get("/api/v1/files?search=report")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 2
    filenames = [item["filename"] for item in search_data["items"]]
    assert "alpha_report.pdf" in filenames
    assert "gamma_report.docx" in filenames
    assert "beta_data.csv" not in filenames


def test_delete_file_and_versions(client: TestClient):
    """Deleting a file must remove all versions and physical stored objects."""
    res = client.post(
        "/api/v1/files/upload",
        files={"file": ("to_delete.txt", BytesIO(b"delete me"), "text/plain")},
    )
    file_id = res.json()["file"]["id"]

    # Delete
    del_res = client.delete(f"/api/v1/files/{file_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Subsequent GET returns 404
    get_res = client.get(f"/api/v1/files/{file_id}")
    assert get_res.status_code == 404

    # Subsequent download returns 404
    dl_res = client.get(f"/api/v1/files/{file_id}/download")
    assert dl_res.status_code == 404
