/**
 * Core type definitions for Cloud Backup System frontend
 */

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'offline';
  app_name: string;
  version: string;
  environment: string;
  storage_provider: string;
  timestamp: string;
}

export interface StorageStats {
  total_files: number;
  total_bytes: number;
  total_readable: string;
  active_provider: string;
  storage_directory: string;
  last_backup_at?: string;
}

export interface FileItem {
  id: string;
  original_filename: string;
  size_bytes: number;
  mime_type: string;
  sha256: string;
  created_at: string;
}

export interface BackupSnapshot {
  id: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  snapshot_timestamp: string;
  files_included: number;
  total_bytes: number;
  notes?: string;
}
