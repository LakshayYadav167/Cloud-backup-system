# REST API Specification (Draft for Phase 2 Implementation)

All endpoints are versioned under the `/api/v1` namespace.

---

## 1. System & Health

### `GET /api/v1/health`
Checks backend liveness and current operational parameters.

- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "app_name": "Cloud Backup System",
  "version": "1.0.0",
  "storage_provider": "local",
  "timestamp": "2026-10-23T19:15:00.000000Z"
}
```

---

## 2. Storage Statistics

### `GET /api/v1/storage/stats`
Returns aggregated disk metrics and file distribution.

- **Response `200 OK`**:
```json
{
  "total_files": 42,
  "total_bytes": 104857600,
  "total_readable": "100.00 MB",
  "active_provider": "local",
  "storage_directory": "./data/storage",
  "last_backup_at": "2026-10-23T18:00:00Z"
}
```

---

## 3. File Operations

### `POST /api/v1/files/upload`
Accepts multipart form-data file payload.

- **Request**:
  - `file`: Binary file stream (max 50 MB)
- **Response `201 Created`**:
```json
{
  "id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "original_filename": "project_report.pdf",
  "size_bytes": 2457600,
  "mime_type": "application/pdf",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "created_at": "2026-10-23T19:15:30Z"
}
```

### `GET /api/v1/files`
Returns paginated/filtered list of uploaded files.

- **Query Parameters**:
  - `search` (string, optional)
  - `limit` (integer, default: 50)
  - `offset` (integer, default: 0)
- **Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
      "original_filename": "project_report.pdf",
      "size_bytes": 2457600,
      "mime_type": "application/pdf",
      "created_at": "2026-10-23T19:15:30Z"
    }
  ],
  "total": 1
}
```

### `GET /api/v1/files/{file_id}/download`
Streams the raw file with appropriate `Content-Disposition` header.

### `DELETE /api/v1/files/{file_id}`
Deletes the file from local storage and removes its metadata from SQLite.

- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "File deleted successfully",
  "file_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a"
}
```

---

## 4. Backup Snapshots

### `POST /api/v1/backups/trigger`
Triggers an immediate snapshot of current tracked storage.

- **Response `202 Accepted`**:
```json
{
  "backup_id": "bfa293c1-01f2-4e41-a1cf-0104e12e3456",
  "status": "COMPLETED",
  "snapshot_timestamp": "2026-10-23T19:16:00Z",
  "files_included": 42,
  "total_bytes": 104857600
}
```

### `GET /api/v1/backups/history`
Returns chronological list of backup snapshots.

- **Response `200 OK`**:
```json
{
  "snapshots": [
    {
      "id": "bfa293c1-01f2-4e41-a1cf-0104e12e3456",
      "status": "COMPLETED",
      "snapshot_timestamp": "2026-10-23T19:16:00Z",
      "files_included": 42,
      "total_bytes": 104857600
    }
  ]
}
```
