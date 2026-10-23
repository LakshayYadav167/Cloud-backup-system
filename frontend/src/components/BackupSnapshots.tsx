import React, { useState } from 'react';
import {
  Clock,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  PlusCircle,
  RefreshCw,
} from 'lucide-react';
import { BackupSnapshot } from '../types';

interface BackupSnapshotsProps {
  snapshots: BackupSnapshot[];
  total: number;
  isLoading: boolean;
  onTriggerBackup: (notes?: string) => Promise<void>;
  onRefresh: () => void;
}

export const BackupSnapshots: React.FC<BackupSnapshotsProps> = ({
  snapshots,
  total,
  isLoading,
  onTriggerBackup,
  onRefresh,
}) => {
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [notes, setNotes] = useState<string>('');
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

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

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-soft-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-semibold text-navy-900 flex items-center space-x-2">
            <Clock className="w-5 h-5 text-emerald-600" />
            <span>Point-in-Time Backup Snapshots</span>
          </h3>
          <p className="text-xs text-slate-500">
            Immutable snapshot manifests capturing the state of all active files ({total} snapshots recorded)
          </p>
        </div>

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
      </div>

      {/* Snapshots Table */}
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

      {/* Snapshot Trigger Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 shadow-soft-lg space-y-4">
            <h4 className="text-base font-bold text-navy-900">Trigger Point-in-Time Snapshot</h4>
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
                      <svg className="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
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
