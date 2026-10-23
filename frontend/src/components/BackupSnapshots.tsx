import React, { useState } from 'react';
import {
  Clock,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  PlusCircle,
  RefreshCw,
  Archive,
  Download,
  AlertTriangle,
  FileCheck,
  Info,
  X,
} from 'lucide-react';
import { BackupSnapshot, ArchiveVerificationResponse, ArchiveRestoreResponse } from '../types';
import { api } from '../services/api';

interface BackupSnapshotsProps {
  snapshots: BackupSnapshot[];
  total: number;
  isLoading: boolean;
  onTriggerBackup: (notes?: string) => Promise<void>;
  onRefresh: () => void;
  onArchiveRestored?: () => void;
}

export const BackupSnapshots: React.FC<BackupSnapshotsProps> = ({
  snapshots,
  total,
  isLoading,
  onTriggerBackup,
  onRefresh,
  onArchiveRestored,
}) => {
  // Sub-view toggle: 'snapshots' (metadata in SQLite) vs 'archives' (portable ZIP packages)
  const [activeSubTab, setActiveSubTab] = useState<'snapshots' | 'archives'>('snapshots');

  // --- Snapshot State ---
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [notes, setNotes] = useState<string>('');
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // --- Archive Export State ---
  const [exportNotes, setExportNotes] = useState<string>('');
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // --- Archive Verification State ---
  const [verifyFile, setVerifyFile] = useState<File | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verifyResult, setVerifyResult] = useState<ArchiveVerificationResponse | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  // --- Archive Restore State ---
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [conflictStrategy, setConflictStrategy] = useState<'rename' | 'skip' | 'replace'>('rename');
  const [confirmRestore, setConfirmRestore] = useState<boolean>(false);
  const [isRestoring, setIsRestoring] = useState<boolean>(false);
  const [restoreResult, setRestoreResult] = useState<ArchiveRestoreResponse | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const copyChecksum = (checksum: string, id: string) => {
    navigator.clipboard.writeText(checksum);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTriggering(true);
    try {
      await onTriggerBackup(notes);
      setNotes('');
      setIsModalOpen(false);
    } finally {
      setIsTriggering(false);
    }
  };

  const handleExportArchive = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      await api.exportArchive(exportNotes);
      setExportNotes('');
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : 'Failed to export archive');
    } finally {
      setIsExporting(false);
    }
  };

  const handleVerifyArchive = async () => {
    if (!verifyFile) return;
    setIsVerifying(true);
    setVerifyError(null);
    setVerifyResult(null);
    try {
      const result = await api.verifyArchive(verifyFile);
      setVerifyResult(result);
    } catch (err: unknown) {
      setVerifyError(err instanceof Error ? err.message : 'Archive verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleRestoreArchive = async () => {
    if (!restoreFile || !confirmRestore) return;
    setIsRestoring(true);
    setRestoreError(null);
    setRestoreResult(null);
    try {
      const result = await api.restoreArchive(restoreFile, conflictStrategy);
      setRestoreResult(result);
      setRestoreFile(null);
      setConfirmRestore(false);
      if (onArchiveRestored) {
        onArchiveRestored();
      }
    } catch (err: unknown) {
      setRestoreError(err instanceof Error ? err.message : 'Archive restoration failed');
    } finally {
      setIsRestoring(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-soft-sm overflow-hidden">
      {/* Sub-view Switcher Header */}
      <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setActiveSubTab('snapshots')}
            className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeSubTab === 'snapshots'
                ? 'bg-white text-navy-900 border border-slate-200 shadow-soft-sm'
                : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
            }`}
          >
            <Clock className="w-4 h-4 text-emerald-600" />
            <span>Point-in-Time Snapshots ({total})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab('archives')}
            className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeSubTab === 'archives'
                ? 'bg-white text-navy-900 border border-slate-200 shadow-soft-sm'
                : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
            }`}
          >
            <Archive className="w-4 h-4 text-sky-600" />
            <span>Portable Archives (.zip)</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800">
              Self-Contained
            </span>
          </button>
        </div>

        {activeSubTab === 'snapshots' && (
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
              title="Refresh snapshot history"
              aria-label="Refresh snapshot history"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition shadow-sm"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Trigger Snapshot</span>
            </button>
          </div>
        )}
      </div>

      {/* SUB-VIEW 1: POINT-IN-TIME SNAPSHOTS */}
      {activeSubTab === 'snapshots' && (
        <>
          <div className="p-4 border-b border-slate-100 bg-slate-50/50">
            <p className="text-xs text-slate-600">
              Immutable metadata snapshot manifests recorded in SQLite, referencing current active file versions and checksums.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/75 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-5">Snapshot ID</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Files Captured</th>
                  <th className="py-3 px-4">Total Footprint</th>
                  <th className="py-3 px-4">Manifest Checksum</th>
                  <th className="py-3 px-5">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-navy-800">
                {isLoading ? (
                  [1, 2, 3].map((i) => (
                    <tr key={i} className="animate-pulse">
                      <td className="py-4 px-5"><div className="h-4 bg-slate-200 rounded w-24" /></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-100 rounded w-16" /></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-100 rounded w-28" /></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-100 rounded w-12" /></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-100 rounded w-16" /></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-100 rounded w-24" /></td>
                      <td className="py-4 px-5"><div className="h-4 bg-slate-100 rounded w-32" /></td>
                    </tr>
                  ))
                ) : snapshots.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center">
                      <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
                        <ShieldCheck className="w-6 h-6" />
                      </div>
                      <h4 className="mt-3 text-sm font-semibold text-navy-900">
                        No Backup Snapshots Generated Yet
                      </h4>
                      <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
                        Click "Trigger Snapshot" to capture an immutable point-in-time state of all active files and their versions.
                      </p>
                    </td>
                  </tr>
                ) : (
                  snapshots.map((snap) => (
                    <tr key={snap.id} className="hover:bg-slate-50/75 transition-colors">
                      <td className="py-3.5 px-5 font-mono text-[11px] text-navy-900 font-semibold truncate max-w-[120px]" title={snap.id}>
                        {snap.id.substring(0, 8)}...
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                          {snap.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 text-[11px]">
                        {new Date(snap.snapshot_timestamp).toLocaleString(undefined, {
                          dateStyle: 'short',
                          timeStyle: 'medium',
                        })}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-navy-900">
                        {snap.total_files} files
                      </td>
                      <td className="py-3.5 px-4 font-medium text-slate-600">
                        {snap.total_readable}
                      </td>
                      <td className="py-3.5 px-4">
                        {snap.checksum ? (
                          <button
                            type="button"
                            onClick={() => copyChecksum(snap.checksum!, snap.id)}
                            className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-[10px] font-mono text-slate-600 transition"
                            title="Click to copy manifest checksum"
                          >
                            <span>{snap.checksum.substring(0, 10)}...</span>
                            {copiedId === snap.id ? (
                              <Check className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3 text-slate-400" />
                            )}
                          </button>
                        ) : (
                          <span className="text-slate-400 text-[10px]">&mdash;</span>
                        )}
                      </td>
                      <td className="py-3.5 px-5 text-slate-500 text-[11px] max-w-xs truncate" title={snap.notes || ''}>
                        {snap.notes || 'Automated snapshot'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* SUB-VIEW 2: PORTABLE BACKUP ARCHIVES */}
      {activeSubTab === 'archives' && (
        <div className="p-6 space-y-6">
          {/* Informational Banner */}
          <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-sky-950 flex items-start space-x-3">
            <Info className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-sky-900">
                Self-Contained, Independently Restorable Backup Archives
              </p>
              <p className="text-sky-800">
                Unlike database metadata snapshots, portable archives package <strong>original binary payloads</strong>, complete <strong>historical versions</strong>, safe paths, and a <strong>v1.0.0 cryptographic SHA-256 manifest</strong> into a standalone ZIP.
                Archives can be verified and restored on clean, isolated installations without relying on the original database or file paths.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Card 1: Export Archive */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-soft-sm space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center space-x-2 text-navy-900 font-semibold text-sm">
                  <Download className="w-4 h-4 text-emerald-600" />
                  <span>1. Export Archive (.zip)</span>
                </div>
                <p className="text-xs text-slate-600">
                  Packages all active files, multi-version histories, and a SHA-256 manifest into a downloadable portable ZIP archive.
                </p>
                <div>
                  <label htmlFor="export-notes" className="block text-[11px] font-semibold text-navy-800 mb-1">
                    Audit Notes (Optional)
                  </label>
                  <input
                    id="export-notes"
                    type="text"
                    value={exportNotes}
                    onChange={(e) => setExportNotes(e.target.value)}
                    placeholder="e.g. Monthly off-site archive"
                    className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    disabled={isExporting}
                  />
                </div>
                {exportError && (
                  <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>{exportError}</span>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={handleExportArchive}
                disabled={isExporting}
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition shadow-sm disabled:opacity-60"
              >
                {isExporting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Packaging Archive...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Export & Download (.zip)</span>
                  </>
                )}
              </button>
            </div>

            {/* Card 2: Verify Archive */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-soft-sm space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center space-x-2 text-navy-900 font-semibold text-sm">
                  <FileCheck className="w-4 h-4 text-sky-600" />
                  <span>2. Verify Archive</span>
                </div>
                <p className="text-xs text-slate-600">
                  Inspects archive structure, decompress limits, format version, and recalculates SHA-256 hashes without modifying state.
                </p>
                <div>
                  <label htmlFor="verify-file" className="block text-[11px] font-semibold text-navy-800 mb-1">
                    Select Archive to Verify
                  </label>
                  <input
                    id="verify-file"
                    type="file"
                    accept=".zip"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setVerifyFile(e.target.files[0]);
                        setVerifyResult(null);
                        setVerifyError(null);
                      }
                    }}
                    className="w-full text-xs text-slate-600 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100"
                    disabled={isVerifying}
                  />
                </div>

                {verifyError && (
                  <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>{verifyError}</span>
                  </div>
                )}

                {verifyResult && (
                  <div
                    className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                      verifyResult.valid
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                        : 'bg-red-50 border-red-200 text-red-950'
                    }`}
                  >
                    <div className="flex items-center space-x-1.5 font-bold">
                      {verifyResult.valid ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span>Verification Passed (Valid)</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-4 h-4 text-red-600" />
                          <span>Verification Failed</span>
                        </>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-700 pt-1">
                      <div>Format: v{verifyResult.format_version || '1.0.0'}</div>
                      <div>Files: {verifyResult.total_files}</div>
                      <div>Versions: {verifyResult.total_versions}</div>
                      <div>Size: {verifyResult.total_readable}</div>
                    </div>
                    {verifyResult.errors.length > 0 && (
                      <div className="pt-1 text-[11px] text-red-700 font-mono">
                        {verifyResult.errors.map((err, idx) => (
                          <div key={idx}>&bull; {err}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={handleVerifyArchive}
                disabled={!verifyFile || isVerifying}
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold bg-sky-600 text-white hover:bg-sky-700 transition shadow-sm disabled:opacity-50"
              >
                {isVerifying ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Verifying Checksums...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Verify Archive</span>
                  </>
                )}
              </button>
            </div>

            {/* Card 3: Restore Archive */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-soft-sm space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center space-x-2 text-navy-900 font-semibold text-sm">
                  <Archive className="w-4 h-4 text-indigo-600" />
                  <span>3. Restore Archive</span>
                </div>
                <p className="text-xs text-slate-600">
                  Pre-verifies SHA-256 hashes, generates isolated system UUIDs, and safely restores files via the configured storage backend.
                </p>

                <div>
                  <label htmlFor="restore-file" className="block text-[11px] font-semibold text-navy-800 mb-1">
                    Select Archive to Restore
                  </label>
                  <input
                    id="restore-file"
                    type="file"
                    accept=".zip"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setRestoreFile(e.target.files[0]);
                        setRestoreResult(null);
                        setRestoreError(null);
                      }
                    }}
                    className="w-full text-xs text-slate-600 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                    disabled={isRestoring}
                  />
                </div>

                <div>
                  <label htmlFor="conflict-strategy-select" className="block text-[11px] font-semibold text-navy-800 mb-1">
                    Conflict Resolution Strategy
                  </label>
                  <select
                    id="conflict-strategy-select"
                    value={conflictStrategy}
                    onChange={(e) => setConflictStrategy(e.target.value as 'rename' | 'skip' | 'replace')}
                    className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-navy-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    disabled={isRestoring}
                  >
                    <option value="rename">Rename (Safe Non-Destructive)</option>
                    <option value="skip">Skip (Keep Existing)</option>
                    <option value="replace">Replace (Overwrite Existing)</option>
                  </select>
                </div>

                <div className="flex items-start space-x-2 pt-1">
                  <input
                    type="checkbox"
                    id="confirm-restore-check"
                    checked={confirmRestore}
                    onChange={(e) => setConfirmRestore(e.target.checked)}
                    className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    disabled={isRestoring}
                  />
                  <label htmlFor="confirm-restore-check" className="text-[11px] text-slate-600 cursor-pointer">
                    I confirm importing this archive into active storage with strategy <strong>{conflictStrategy}</strong>.
                  </label>
                </div>

                {restoreError && (
                  <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>{restoreError}</span>
                  </div>
                )}

                {restoreResult && (
                  <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs space-y-1 text-emerald-950">
                    <div className="flex items-center space-x-1.5 font-bold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>{restoreResult.message}</span>
                    </div>
                    <div className="text-[11px] text-slate-700">
                      Imported {restoreResult.imported_files_count} files ({restoreResult.imported_versions_count} versions), skipped {restoreResult.skipped_files_count}.
                    </div>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={handleRestoreArchive}
                disabled={!restoreFile || !confirmRestore || isRestoring}
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition shadow-sm disabled:opacity-50"
              >
                {isRestoring ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Restoring Archive...</span>
                  </>
                ) : (
                  <>
                    <Archive className="w-3.5 h-3.5" />
                    <span>Execute Restore</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Snapshot Trigger Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 shadow-soft-lg space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-base font-bold text-navy-900">Trigger Point-in-Time Snapshot</h4>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              This creates an immutable backup record linking every current file version and generates an aggregate SHA-256 manifest.
            </p>

            <form onSubmit={handleCreateSnapshot} className="space-y-4">
              <div>
                <label htmlFor="snapshot-notes" className="block text-xs font-semibold text-navy-800 mb-1">
                  Snapshot Description / Notes (Optional)
                </label>
                <input
                  id="snapshot-notes"
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Pre-deployment backup, end of sprint snapshot"
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition"
                  disabled={isTriggering}
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isTriggering}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isTriggering}
                  className={`inline-flex items-center px-4 py-1.5 text-xs font-semibold rounded-lg text-white bg-emerald-600 hover:bg-emerald-700 transition shadow-sm ${
                    isTriggering ? 'opacity-70 cursor-not-allowed' : ''
                  }`}
                >
                  {isTriggering ? (
                    <>
                      <RefreshCw className="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-white" />
                      <span>Creating Snapshot...</span>
                    </>
                  ) : (
                    <span>Create Snapshot</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
