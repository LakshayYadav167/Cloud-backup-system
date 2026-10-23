# REST API Specification (Implemented Phase 2 Endpoints)

All API endpoints are versioned under the `/api/v1` namespace.

Interactive OpenAPI / Swagger documentation is available at `/docs` and ReDoc at `/redoc`.

---

## 1. System & Operational Diagnostics

### `GET /`
Returns root project metadata, documentation links, active storage mode, and primary endpoint paths.

- **Response `200 OK`**:
```json
{
  "project": "Cloud Backup System API",
  "version": "1.0.0",
  "docs_url": "/docs",
  "health_check": "/api/v1/health",
  "api_v1_endpoints": {
    "health": "/api/v1/health",
    "files": "/api/v1/files",
    "upload": "/api/v1/files/upload",
    "storage_stats": "/api/v1/storage/stats",
    "backups_trigger": "/api/v1/backups/trigger",
    "backups_history": "/api/v1/backups/history"
  },
  "storage_mode": "local",
  "message": "Cloud Backup System API is running successfully."
}
```

### `GET /api/v1/health`
Reports system liveness, active storage backend, and SQLite database connectivity status.

- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "Cloud Backup System API",
  "version": "1.0.0",
  "environment": "development",
  "storage_provider": "local",
  "database_status": "connected",
  "timestamp": "2026-10-23T23:25:00.000000Z"
}
```

---

## 2. File Storage & Versioning Operations

### `POST /api/v1/files/upload`
Uploads a file payload using `multipart/form-data`.
- If the filename is new: creates a new logical file with `version_number = 1`.
- If the filename already exists: preserves historical versions, creates a new unique immutable object key, and creates `version_number = N + 1`.

- **Form Fields**:
  - `file`: Binary file stream (required, max configured `MAX_UPLOAD_SIZE_MB`, default 50 MB).
  - `summary`: Optional string note describing changes for this version.
- **Response `201 Created`**:
```json
{
  "file": {
    "id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b",
    "filename": "database_design.pdf",
    "content_type": "application/pdf",
    "size_bytes": 2457600,
    "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
    "current_version_id": "78c8a14b-57a9-4673-89b1-e0c1f5d688cf",
    "current_version_number": 2,
    "total_versions": 2,
    "created_at": "2026-10-23 23:20:00",
    "updated_at": "2026-10-23 23:25:00"
  },
  "version": {
    "id": "78c8a14b-57a9-4673-89b1-e0c1f5d688cf",
    "file_id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b",
    "version_number": 2,
    "size_bytes": 2457600,
    "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
    "content_type": "application/pdf",
    "change_summary": "Added index optimization benchmarks",
    "created_at": "2026-10-23 23:25:00",
    "is_current": true
  },
  "message": "File 'database_design.pdf' uploaded successfully as version 2."
}
```
- **Error Responses**:
  - `400 Bad Request`: Empty filename or reserved Windows device name (`CON`, `PRN`, `AUX`, `NUL`).
  - `413 Payload Too Large`: Payload exceeds configured maximum size limit.
  - `422 Unprocessable Entity`: Missing file field.

### `GET /api/v1/files`
Returns a paginated list of active files with current version details and version count.

- **Query Parameters**:
  - `search` (string, optional): Substring filter on filename.
  - `limit` (integer, default: 50, max: 100): Page size.
  - `offset` (integer, default: 0): Pagination offset.
- **Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b",
      "filename": "database_design.pdf",
      "content_type": "application/pdf",
      "size_bytes": 2457600,
      "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
      "current_version_id": "78c8a14b-57a9-4673-89b1-e0c1f5d688cf",
      "current_version_number": 2,
      "total_versions": 2,
      "created_at": "2026-10-23 23:20:00",
      "updated_at": "2026-10-23 23:25:00"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### `GET /api/v1/files/{file_id}`
Retrieves metadata for a single logical file.

- **Response `200 OK`**: Returns `FileItemResponse`.
- **Response `404 Not Found`**: File ID does not exist or has been deleted.

### `GET /api/v1/files/{file_id}/versions`
Returns the complete version history for a file in descending chronological order.

- **Response `200 OK`**:
```json
[
  {
    "id": "78c8a14b-57a9-4673-89b1-e0c1f5d688cf",
    "file_id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b",
    "version_number": 2,
    "size_bytes": 2457600,
    "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
    "content_type": "application/pdf",
    "change_summary": "Added index optimization benchmarks",
    "created_at": "2026-10-23 23:25:00",
    "is_current": true
  },
  {
    "id": "11a0b33c-2222-4444-9999-000000000001",
    "file_id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b",
    "version_number": 1,
    "size_bytes": 1048576,
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "content_type": "application/pdf",
    "change_summary": "Initial upload",
    "created_at": "2026-10-23 23:20:00",
    "is_current": false
  }
]
```

### `GET /api/v1/files/{file_id}/download`
Streams file binary content.
- Defaults to streaming the current active version.
- If `?version_id={id}` query parameter is supplied, streams that exact historical version.

- **Headers**:
  - `Content-Disposition: attachment; filename="{filename}"`
  - `Content-Type: {content_type}`
  - `Content-Length: {size_bytes}`
  - `ETag: "{sha256}"`
- **Response `200 OK`**: Binary stream.
- **Response `404 Not Found`**: File or version not found.

### `POST /api/v1/files/{file_id}/restore/{version_id}`
Restores the file's current state to a previous historical version.
- Preserves all historical version records and object keys (immutability).
- Updates the logical file pointer `current_version_id`.
- Future downloads immediately serve the restored version content.

- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "File 'database_design.pdf' restored to version 1.",
  "file": {
    "id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b",
    "filename": "database_design.pdf",
    "current_version_id": "11a0b33c-2222-4444-9999-000000000001",
    "current_version_number": 1,
    "total_versions": 2
  },
  "restored_version": {
    "id": "11a0b33c-2222-4444-9999-000000000001",
    "version_number": 1,
    "is_current": true
  }
}
```

### `DELETE /api/v1/files/{file_id}`
Permanently deletes a file, removing all historical versions and physical disk/S3 objects.

- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "File and all historical versions deleted successfully.",
  "file_id": "e6a2b53c-1b3a-4ef6-bb4d-17684992911b"
}
```

---

## 3. Storage Capacity & Quota Metrics

### `GET /api/v1/storage/stats`
Returns aggregated capacity usage, quota percentage, active driver, and last backup timestamp. Internal host paths are masked.

- **Response `200 OK`**:
```json
{
  "provider": "local",
  "total_files": 12,
  "total_versions": 25,
  "total_bytes": 15728640,
  "total_readable": "15.00 MB",
  "quota_bytes": 52428800,
  "quota_readable": "50.00 MB",
  "quota_percent_used": 30.0,
  "base_location": "./data/storage",
  "last_backup_at": "2026-10-23 23:25:00"
}
```

---

## 4. Backup Snapshots & Audit Trail

### `POST /api/v1/backups/trigger`
Creates a point-in-time immutable backup snapshot of all currently active files and their versions, producing an aggregate manifest checksum.

- **Query Parameters**:
  - `notes` (string, optional): Description or reason for snapshot.
- **Response `201 Created`**:
```json
{
  "id": "c1f7a0b3-9000-4712-b234-555566667777",
  "status": "COMPLETED",
  "snapshot_timestamp": "2026-10-23 23:26:00",
  "total_files": 12,
  "total_bytes": 15728640,
  "total_readable": "15.00 MB",
  "checksum": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
  "notes": "Manual pre-deployment backup"
}
```

### `GET /api/v1/backups/history`
Returns chronological audit list of backup snapshots.

- **Response `200 OK`**:
```json
{
  "snapshots": [
    {
      "id": "c1f7a0b3-9000-4712-b234-555566667777",
      "status": "COMPLETED",
      "snapshot_timestamp": "2026-10-23 23:26:00",
      "total_files": 12,
      "total_bytes": 15728640,
      "total_readable": "15.00 MB",
      "checksum": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
      "notes": "Manual pre-deployment backup"
    }
  ],
  "total": 1
}
```

---

## 5. Portable Backup Archives (Phase 7)

Portable backup archives are self-contained, independently restorable standard ZIP packages containing original binary file contents, complete historical versions, and a root `manifest.json` (format version `1.0.0`) with cryptographic SHA-256 hashes. Unlike Phase 2 metadata snapshots, archives are fully restorable on clean, isolated installations without relying on the original database or file storage paths.

### Archive File Format & Layout
```text
backup_archive_20261024_030000.zip
├── manifest.json                  # Root cryptographic manifest (v1.0.0)
└── blobs/
    ├── {version_id_1}_report.pdf  # Raw binary payload for file 1 version 1
    ├── {version_id_2}_report.pdf  # Raw binary payload for file 1 version 2
    └── {version_id_3}_data.csv    # Raw binary payload for file 2 version 1
```

#### `manifest.json` Schema (v1.0.0)
```json
{
  "archive_format_version": "1.0.0",
  "generator": "CloudBackupSystem/1.0.0",
  "exported_at": "2026-10-24T03:00:00Z",
  "notes": "Monthly off-site archive",
  "total_files": 2,
  "total_versions": 3,
  "total_bytes": 3145728,
  "files": [
    {
      "original_filename": "report.pdf",
      "safe_filename": "report.pdf",
      "content_type": "application/pdf",
      "current_version_number": 2,
      "total_versions": 2,
      "versions": [
        {
          "archive_blob_path": "blobs/ver-1_report.pdf",
          "version_number": 1,
          "size_bytes": 1048576,
          "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "change_summary": "Initial draft",
          "created_at": "2026-10-23T20:00:00Z",
          "is_current": false
        },
        {
          "archive_blob_path": "blobs/ver-2_report.pdf",
          "version_number": 2,
          "size_bytes": 2097152,
          "sha256": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
          "change_summary": "Final version",
          "created_at": "2026-10-23T21:00:00Z",
          "is_current": true
        }
      ]
    }
  ]
}
```

---

### `GET /api/v1/archives/export` / `POST /api/v1/archives/export`
Exports all active files and historical versions into a downloadable portable ZIP archive.

- **Query Parameters**:
  - `notes` (string, optional): Audit description embedded in `manifest.json`.
- **Response `200 OK`**:
  - `Content-Type`: `application/zip`
  - `Content-Disposition`: `attachment; filename="backup_archive_YYYYMMDD_HHMMSS.zip"`
  - Body: Binary ZIP stream.
- **Error Responses**:
  - `409 Conflict`: If any required storage object is missing from disk/S3 (ensures incomplete backups are never silently generated).

---

### `POST /api/v1/archives/verify`
Dry-run verification of an uploaded archive without modifying application state or database records.

- **Form Data**:
  - `file`: ZIP file to inspect (required).
- **Security & Integrity Checks**:
  - Max archive upload size: 100 MB.
  - Max uncompressed size limit: 250 MB (zip-bomb defense).
  - Max entry count: 1,000 entries.
  - Max compression ratio: 100:1.
  - Rejection of path traversal (`..`, `/`, `\`, drive letters `C:`).
  - Rejection of Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, etc.).
  - Rejection of unknown manifest versions.
  - Cryptographic verification: Recomputes SHA-256 hash of each uncompressed blob and matches against `manifest.json`.
- **Response `200 OK`**:
```json
{
  "valid": true,
  "format_version": "1.0.0",
  "generator": "CloudBackupSystem/1.0.0",
  "exported_at": "2026-10-24T03:00:00Z",
  "total_files": 2,
  "total_versions": 3,
  "total_bytes": 3145728,
  "total_readable": "3.00 MB",
  "errors": [],
  "warnings": []
}
```
If verification fails, `valid` is `false` and `errors` details all detected anomalies (e.g. `SHA-256 mismatch for blobs/ver-1_report.pdf`, `Path traversal detected`).

---

### `POST /api/v1/archives/restore`
Imports files and full version histories from a verified archive into the active storage and database tier.

- **Form Data**:
  - `file`: ZIP archive file (required).
  - `conflict_strategy`: String collision strategy for existing filenames:
    - `"rename"` (default): Appends `_imported_{short_uuid}` to colliding filenames, preserving existing files and their versions.
    - `"skip"`: Skips colliding files; imports only non-colliding files.
    - `"replace"`: Purges colliding existing files and all their historical versions, replacing them with archive versions.
- **Safety Guarantees**:
  - Cryptographically verifies all SHA-256 hashes before initiating imports.
  - Generates new system UUIDs and storage keys (never trusts archive-supplied IDs).
  - Restores via the active `StorageProvider` abstraction (fully compatible with local filesystem or Floci S3).
  - Storage rollback: If database transaction fails, restored storage objects are purged to prevent orphaned blobs.
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Successfully imported 2 files and 3 versions from backup archive.",
  "conflict_strategy": "rename",
  "imported_files_count": 2,
  "imported_versions_count": 3,
  "skipped_files_count": 0,
  "details": [
    "Restored file 'report.pdf' (2 versions)",
    "Restored file 'data.csv' (1 versions)"
  ]
}
```

