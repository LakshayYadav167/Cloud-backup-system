/**
 * TypeScript interfaces matching the backend FastAPI schemas.
 * Derived from backend/app/models/schemas.py.
 */

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'offline';
  app_name: string;
  version: string;
  environment: string;
  storage_provider: string;
  database_status: string;
  storage_status?: string;
  timestamp: string;
}

export interface FileItem {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  current_version_id?: string | null;
  current_version_number: number;
  total_versions: number;
  created_at: string;
  updated_at: string;
}

export interface FileVersionSummary {
  id: string;
  file_id: string;
  version_number: number;
  size_bytes: number;
  sha256: string;
  content_type: string;
  change_summary: string;
  created_at: string;
  is_current: boolean;
}

export interface FileListResponse {
  items: FileItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface FileUploadResponse {
  file: FileItem;
  version: FileVersionSummary;
  message: string;
}

export interface FileRestoreResponse {
  success: boolean;
  message: string;
  file: FileItem;
  restored_version: FileVersionSummary;
}

export interface FileDeleteResponse {
  success: boolean;
  message: string;
  file_id: string;
}

export interface StorageStats {
  provider: string;
  total_files: number;
  total_versions: number;
  total_bytes: number;
  total_readable: string;
  quota_bytes: number;
  quota_readable: string;
  quota_percent_used: number;
  base_location: string;
  last_backup_at?: string | null;
}

export interface BackupSnapshot {
  id: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  snapshot_timestamp: string;
  total_files: number;
  total_bytes: number;
  total_readable: string;
  checksum?: string | null;
  notes?: string | null;
}

export interface BackupHistoryResponse {
  snapshots: BackupSnapshot[];
  total: number;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
}

export interface ArchiveVerificationResponse {
  valid: boolean;
  format_version?: string | null;
  generator?: string | null;
  exported_at?: string | null;
  total_files: number;
  total_versions: number;
  total_bytes: number;
  total_readable: string;
  errors: string[];
  warnings: string[];
}

export interface ArchiveRestoreResponse {
  success: boolean;
  message: string;
  conflict_strategy: string;
  imported_files_count: number;
  imported_versions_count: number;
  skipped_files_count: number;
  details: string[];
}

