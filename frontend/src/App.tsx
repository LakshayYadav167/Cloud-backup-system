import React, { useEffect, useState, useCallback } from 'react';
import {
  FileText,
  Clock,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import { api } from './services/api';
import {
  FileItem,
  FileVersionSummary,
  HealthResponse,
  StorageStats,
  BackupSnapshot,
  ToastMessage,
} from './types';
import { Navbar } from './components/Navbar';
import { StorageStatsCard } from './components/StorageStatsCard';
import { UploadArea } from './components/UploadArea';
import { FileList } from './components/FileList';
import { VersionDrawer } from './components/VersionDrawer';
import { BackupSnapshots } from './components/BackupSnapshots';
import { ConfirmModal } from './components/ConfirmModal';
import { ToastContainer } from './components/Toast';

export const App: React.FC = () => {
  // Navigation State
  const [activeTab, setActiveTab] = useState<'files' | 'backups'>('files');

  // Backend Data State
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [totalFiles, setTotalFiles] = useState<number>(0);
  const [snapshots, setSnapshots] = useState<BackupSnapshot[]>([]);
  const [totalSnapshots, setTotalSnapshots] = useState<number>(0);

  // Search & Pagination State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [fileOffset, setFileOffset] = useState<number>(0);
  const fileLimit = 50;

  // Loading States
  const [isLoadingStats, setIsLoadingStats] = useState<boolean>(true);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [isLoadingSnapshots, setIsLoadingSnapshots] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Modal & Drawer State
  const [selectedFileForVersions, setSelectedFileForVersions] = useState<FileItem | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    confirmLabel: string;
    variant: 'danger' | 'warning' | 'primary';
    isLoading: boolean;
    onConfirm: () => Promise<void>;
  }>({
    isOpen: false,
    title: '',
    message: '',
    confirmLabel: 'Confirm',
    variant: 'danger',
    isLoading: false,
    onConfirm: async () => {},
  });

  // Toast Helper
  const addToast = (type: 'success' | 'error' | 'info' | 'warning', title: string, message?: string) => {
    const id = `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Fetch Storage Stats & Health
  const loadStatsAndHealth = useCallback(async () => {
    setIsLoadingStats(true);
    try {
      const [hData, sData] = await Promise.all([
        api.getHealth().catch(() => ({
          status: 'offline' as const,
          app_name: 'Cloud Backup System API',
          version: '1.0.0',
          environment: 'offline',
          storage_provider: 'local',
          database_status: 'disconnected',
          timestamp: new Date().toISOString(),
        })),
        api.getStorageStats().catch(() => null),
      ]);

      setHealth(hData);
      setStorageStats(sData);
      setApiError(hData.status === 'offline' ? 'Backend API server is unreachable on port 8000.' : null);
    } finally {
      setIsLoadingStats(false);
    }
  }, []);

  // Fetch Files
  const loadFiles = useCallback(async (query: string, offset: number) => {
    setIsLoadingFiles(true);
    try {
      const data = await api.listFiles(query, fileLimit, offset);
      setFiles(data.items);
      setTotalFiles(data.total);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load files';
      addToast('error', 'Error Loading Files', msg);
    } finally {
      setIsLoadingFiles(false);
    }
  }, [fileLimit]);

  // Fetch Snapshots
  const loadSnapshots = useCallback(async () => {
    setIsLoadingSnapshots(true);
    try {
      const data = await api.getBackupHistory(50, 0);
      setSnapshots(data.snapshots);
      setTotalSnapshots(data.total);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load backup snapshots';
      addToast('error', 'Error Loading Backups', msg);
    } finally {
      setIsLoadingSnapshots(false);
    }
  }, []);

  // Refresh All Dashboard Data
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([
      loadStatsAndHealth(),
      loadFiles(searchQuery, fileOffset),
      loadSnapshots(),
    ]);
    setIsRefreshing(false);
    addToast('info', 'Dashboard Refreshed', 'Latest storage metrics and file inventory synced.');
  };

  // Initial Load
  useEffect(() => {
    loadStatsAndHealth();
    loadFiles(searchQuery, fileOffset);
    loadSnapshots();
  }, [loadStatsAndHealth, loadFiles, loadSnapshots, searchQuery, fileOffset]);

  // Handle Search Input Change
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    setFileOffset(0);
  };

  // Handle Page Change
  const handlePageChange = (newOffset: number) => {
    setFileOffset(newOffset);
  };

  // File Download Action
  const handleDownload = async (file: FileItem) => {
    try {
      await api.downloadFile(file.id, file.filename);
      addToast('success', 'Download Started', `Downloading ${file.filename}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Download failed';
      addToast('error', 'Download Failed', msg);
    }
  };

  // Version Download Action
  const handleDownloadVersion = async (file: FileItem, versionId: string) => {
    try {
      await api.downloadFile(file.id, file.filename, versionId);
      addToast('success', 'Version Downloaded', `Downloaded historical version for ${file.filename}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Download failed';
      addToast('error', 'Download Failed', msg);
    }
  };

  // File Delete Flow
  const handleDeleteRequest = (file: FileItem) => {
    setConfirmModal({
      isOpen: true,
      title: 'Delete Stored File',
      message: `Permanently delete "${file.filename}" and all ${file.total_versions} of its historical backup versions from storage? This action cannot be undone.`,
      confirmLabel: 'Delete File',
      variant: 'danger',
      isLoading: false,
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isLoading: true }));
        try {
          await api.deleteFile(file.id);
          addToast('success', 'File Deleted', `"${file.filename}" was permanently deleted.`);
          setConfirmModal((prev) => ({ ...prev, isOpen: false, isLoading: false }));
          loadFiles(searchQuery, fileOffset);
          loadStatsAndHealth();
          if (selectedFileForVersions?.id === file.id) {
            setSelectedFileForVersions(null);
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : 'Failed to delete file';
          addToast('error', 'Delete Failed', msg);
          setConfirmModal((prev) => ({ ...prev, isLoading: false }));
        }
      },
    });
  };

  // Version Restore Flow
  const handleRestoreRequest = (file: FileItem, version: FileVersionSummary) => {
    setConfirmModal({
      isOpen: true,
      title: 'Restore Historical Version',
      message: `Restore "${file.filename}" to Version ${version.version_number}? Historical versions remain safe and immutable. Subsequent downloads will serve Version ${version.version_number}.`,
      confirmLabel: `Restore to Version ${version.version_number}`,
      variant: 'primary',
      isLoading: false,
      onConfirm: async () => {
        setConfirmModal((prev) => ({ ...prev, isLoading: true }));
        try {
          const resp = await api.restoreFileVersion(file.id, version.id);
          addToast('success', 'Version Restored', resp.message);
          setConfirmModal((prev) => ({ ...prev, isOpen: false, isLoading: false }));
          // Refresh views
          loadFiles(searchQuery, fileOffset);
          loadStatsAndHealth();
          setSelectedFileForVersions(resp.file);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : 'Restore failed';
          addToast('error', 'Restore Failed', msg);
          setConfirmModal((prev) => ({ ...prev, isLoading: false }));
        }
      },
    });
  };

  // Backup Snapshot Trigger Flow
  const handleTriggerBackup = async (notes?: string) => {
    try {
      const snap = await api.triggerBackup(notes);
      addToast(
        'success',
        'Snapshot Generated',
        `Captured ${snap.total_files} active files (${snap.total_readable}). Manifest checksum: ${snap.checksum?.substring(0, 10)}...`
      );
      loadSnapshots();
      loadStatsAndHealth();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Snapshot creation failed';
      addToast('error', 'Snapshot Failed', msg);
      throw err;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-navy-900 selection:bg-emerald-500 selection:text-white">
      {/* Toast Notifications Container */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />

      {/* Top Navigation */}
      <Navbar
        health={health}
        storageStats={storageStats}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Backend API Connection Warning */}
        {apiError && (
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-soft-sm">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
              <div>
                <p className="text-xs font-bold">FastAPI Backend Connection Unavailable</p>
                <p className="text-xs text-amber-800">
                  Ensure the backend is running at <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">http://127.0.0.1:8000</code>.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-600 text-white hover:bg-amber-700 transition shrink-0"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              <span>Retry Connection</span>
            </button>
          </div>
        )}

        {/* Real Storage Statistics Cards */}
        <StorageStatsCard stats={storageStats} isLoading={isLoadingStats} />

        {/* Primary Functional Area Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* File Upload Section */}
          <div className="lg:col-span-1 space-y-4">
            <UploadArea
              maxSizeMb={storageStats?.quota_bytes ? Math.round(storageStats.quota_bytes / (1024 * 1024)) : 50}
              onUploadSuccess={(resp) => {
                addToast('success', 'File Uploaded', resp.message);
                loadFiles(searchQuery, fileOffset);
                loadStatsAndHealth();
              }}
              onUploadError={(msg) => addToast('error', 'Upload Error', msg)}
            />
          </div>

          {/* Files Inventory & Backup Snapshots Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* View Selector Tabs */}
            <div className="flex space-x-2 border-b border-slate-200 pb-2">
              <button
                type="button"
                onClick={() => setActiveTab('files')}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                  activeTab === 'files'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-soft-sm'
                    : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>File Inventory ({totalFiles})</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('backups')}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition ${
                  activeTab === 'backups'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-soft-sm'
                    : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>Backup Snapshots ({totalSnapshots})</span>
              </button>
            </div>

            {/* Tab 1: File Inventory */}
            {activeTab === 'files' && (
              <FileList
                files={files}
                total={totalFiles}
                limit={fileLimit}
                offset={fileOffset}
                searchQuery={searchQuery}
                isLoading={isLoadingFiles}
                onSearchChange={handleSearchChange}
                onPageChange={handlePageChange}
                onDownload={handleDownload}
                onViewVersions={(f) => setSelectedFileForVersions(f)}
                onDelete={handleDeleteRequest}
              />
            )}

            {/* Tab 2: Backup Snapshots */}
            {activeTab === 'backups' && (
              <BackupSnapshots
                snapshots={snapshots}
                total={totalSnapshots}
                isLoading={isLoadingSnapshots}
                onTriggerBackup={handleTriggerBackup}
                onRefresh={loadSnapshots}
                onArchiveRestored={() => {
                  loadFiles(searchQuery, fileOffset);
                  loadStatsAndHealth();
                  loadSnapshots();
                  addToast('info', 'Data Synced', 'Archive import completed. File inventory and metrics updated.');
                }}
              />
            )}
          </div>
        </div>
      </main>

      {/* Version History Drawer */}
      <VersionDrawer
        file={selectedFileForVersions}
        onClose={() => setSelectedFileForVersions(null)}
        onRestoreRequest={handleRestoreRequest}
        onDownloadVersion={handleDownloadVersion}
      />

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmLabel={confirmModal.confirmLabel}
        variant={confirmModal.variant}
        isLoading={confirmModal.isLoading}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>
            <span className="font-semibold text-navy-900">Cloud Backup System</span> &mdash; Automated Storage &amp; Disaster Recovery
          </div>
          <div className="flex items-center space-x-3">
            <span>React + Vite + FastAPI + SQLite</span>
            <span>&bull;</span>
            <span className="inline-flex items-center text-emerald-600 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              Backup &amp; Recovery Active
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
