/**
 * Centralized typed API service for Cloud Backup System.
 * Connects to the FastAPI backend versioned under /api/v1.
 */

import {
  ArchiveRestoreResponse,
  ArchiveVerificationResponse,
  BackupHistoryResponse,
  BackupSnapshot,
  FileDeleteResponse,
  FileItem,
  FileListResponse,
  FileRestoreResponse,
  FileUploadResponse,
  FileVersionSummary,
  HealthResponse,
  StorageStats,
} from '../types';

// Use environment configuration or Vite dev server proxy default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        if (typeof errJson.detail === 'string') {
          errorDetail = errJson.detail;
        } else if (Array.isArray(errJson.detail)) {
          // Pydantic validation errors array
          errorDetail = errJson.detail.map((e: { msg?: string }) => e.msg || 'Validation error').join(', ');
        }
      }
    } catch {
      // Body was not JSON
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /**
   * Health and diagnostic check
   */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<HealthResponse>(res);
  },

  /**
   * Aggregated storage and quota metrics
   */
  async getStorageStats(): Promise<StorageStats> {
    const res = await fetch(`${API_BASE_URL}/storage/stats`);
    return handleResponse<StorageStats>(res);
  },

  /**
   * List files with optional search and pagination
   */
  async listFiles(search?: string, limit: number = 50, offset: number = 0): Promise<FileListResponse> {
    const params = new URLSearchParams();
    if (search && search.trim()) {
      params.append('search', search.trim());
    }
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const res = await fetch(`${API_BASE_URL}/files?${params.toString()}`);
    return handleResponse<FileListResponse>(res);
  },

  /**
   * Retrieve single file metadata
   */
  async getFile(fileId: string): Promise<FileItem> {
    const res = await fetch(`${API_BASE_URL}/files/${fileId}`);
    return handleResponse<FileItem>(res);
  },

  /**
   * Upload a file (new file or new version)
   */
  async uploadFile(file: File, summary?: string): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (summary && summary.trim()) {
      formData.append('summary', summary.trim());
    }

    const res = await fetch(`${API_BASE_URL}/files/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<FileUploadResponse>(res);
  },

  /**
   * List all historical versions for a file
   */
  async getFileVersions(fileId: string): Promise<FileVersionSummary[]> {
    const res = await fetch(`${API_BASE_URL}/files/${fileId}/versions`);
    return handleResponse<FileVersionSummary[]>(res);
  },

  /**
   * Download a file (current version or specific historical version)
   */
  async downloadFile(fileId: string, filename: string, versionId?: string): Promise<void> {
    const url = new URL(`${API_BASE_URL}/files/${fileId}/download`, window.location.origin);
    if (versionId) {
      url.searchParams.append('version_id', versionId);
    }

    const res = await fetch(url.toString());
    if (!res.ok) {
      await handleResponse(res); // Will throw appropriate error
      return;
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);
  },

  /**
   * Restore a historical file version
   */
  async restoreFileVersion(fileId: string, versionId: string): Promise<FileRestoreResponse> {
    const res = await fetch(`${API_BASE_URL}/files/${fileId}/restore/${versionId}`, {
      method: 'POST',
    });
    return handleResponse<FileRestoreResponse>(res);
  },

  /**
   * Permanently delete a file and all versions
   */
  async deleteFile(fileId: string): Promise<FileDeleteResponse> {
    const res = await fetch(`${API_BASE_URL}/files/${fileId}`, {
      method: 'DELETE',
    });
    return handleResponse<FileDeleteResponse>(res);
  },

  /**
   * Trigger a point-in-time backup snapshot
   */
  async triggerBackup(notes?: string): Promise<BackupSnapshot> {
    const params = new URLSearchParams();
    if (notes && notes.trim()) {
      params.append('notes', notes.trim());
    }
    const res = await fetch(`${API_BASE_URL}/backups/trigger?${params.toString()}`, {
      method: 'POST',
    });
    return handleResponse<BackupSnapshot>(res);
  },

  /**
   * Retrieve chronological backup snapshot history
   */
  async getBackupHistory(limit: number = 50, offset: number = 0): Promise<BackupHistoryResponse> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const res = await fetch(`${API_BASE_URL}/backups/history?${params.toString()}`);
    return handleResponse<BackupHistoryResponse>(res);
  },

  /**
   * Export portable backup archive as a downloadable ZIP
   */
  async exportArchive(notes?: string): Promise<void> {
    const params = new URLSearchParams();
    if (notes && notes.trim()) {
      params.append('notes', notes.trim());
    }
    const res = await fetch(`${API_BASE_URL}/archives/export?${params.toString()}`);
    if (!res.ok) {
      await handleResponse(res);
      return;
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;

    let filename = `backup_archive_${new Date().toISOString().replace(/[:.]/g, '-')}.zip`;
    const disposition = res.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);
  },

  /**
   * Verify an uploaded backup archive (.zip) integrity without importing
   */
  async verifyArchive(file: File): Promise<ArchiveVerificationResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE_URL}/archives/verify`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ArchiveVerificationResponse>(res);
  },

  /**
   * Restore/import an archive into the system with specified collision strategy
   */
  async restoreArchive(file: File, conflictStrategy: string = 'rename'): Promise<ArchiveRestoreResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conflict_strategy', conflictStrategy);
    const res = await fetch(`${API_BASE_URL}/archives/restore`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ArchiveRestoreResponse>(res);
  },
};

