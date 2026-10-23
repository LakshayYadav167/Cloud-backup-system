import React, { useEffect, useState } from 'react';
import {
  History,
  X,
  Download,
  RotateCcw,
  CheckCircle2,
  Copy,
  Check,
  AlertCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { FileItem, FileVersionSummary } from '../types';

interface VersionDrawerProps {
  file: FileItem | null;
  onClose: () => void;
  onRestoreRequest: (file: FileItem, version: FileVersionSummary) => void;
  onDownloadVersion: (file: FileItem, versionId: string) => void;
}

export const VersionDrawer: React.FC<VersionDrawerProps> = ({
  file,
  onClose,
  onRestoreRequest,
  onDownloadVersion,
}) => {
  const [versions, setVersions] = useState<FileVersionSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (!file) return;

    let isMounted = true;
    const fetchVersions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getFileVersions(file.id);
        if (isMounted) setVersions(data);
      } catch (err: unknown) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load versions');
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchVersions();
    return () => {
      isMounted = false;
    };
  }, [file]);

  if (!file) return null;

  const copyHash = (hash: string, id: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/40 backdrop-blur-xs animate-fade-in">
      <div className="bg-white w-full max-w-lg h-full shadow-2xl border-l border-slate-200 flex flex-col animate-slide-left">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-navy-900 truncate max-w-xs" title={file.filename}>
                {file.filename}
              </h3>
              <p className="text-xs text-slate-500">
                Immutable Backup Version History ({versions.length} versions)
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition"
            aria-label="Close version history"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content List */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 bg-slate-100 rounded-xl p-4" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : versions.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No historical versions recorded.
            </div>
          ) : (
            versions.map((ver) => (
              <div
                key={ver.id}
                className={`p-4 rounded-xl border transition-all ${
                  ver.is_current
                    ? 'border-emerald-300 bg-emerald-50/30 ring-1 ring-emerald-400/40 shadow-soft-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-navy-900">
                        Version {ver.version_number}
                      </span>
                      {ver.is_current && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 italic">
                      "{ver.change_summary || 'No notes provided'}"
                    </p>
                  </div>

                  <div className="text-right">
                    <div className="text-xs font-bold text-navy-900">
                      {formatFileSize(ver.size_bytes)}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {new Date(ver.created_at).toLocaleString(undefined, {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      })}
                    </div>
                  </div>
                </div>

                {/* SHA-256 Checksum snippet */}
                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                  <div className="flex items-center space-x-1.5 font-mono text-[10px] text-slate-500">
                    <span>SHA-256:</span>
                    <button
                      type="button"
                      onClick={() => copyHash(ver.sha256, ver.id)}
                      className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
                      title="Click to copy SHA-256 checksum"
                    >
                      <span>{ver.sha256.substring(0, 12)}...</span>
                      {copiedId === ver.id ? (
                        <Check className="w-3 h-3 text-emerald-600" />
                      ) : (
                        <Copy className="w-3 h-3 text-slate-400" />
                      )}
                    </button>
                  </div>

                  {/* Version Actions */}
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => onDownloadVersion(file, ver.id)}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium border border-slate-200 text-slate-700 hover:bg-slate-50 transition"
                      title="Download this version"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download</span>
                    </button>

                    {!ver.is_current && (
                      <button
                        type="button"
                        onClick={() => onRestoreRequest(file, ver)}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition shadow-xs"
                        title="Restore this version as active"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Restore</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer info note */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500">
          <p>
            Historical objects are immutable on disk. Restoring a version updates the active pointer without overwriting or deleting historical records.
          </p>
        </div>
      </div>
    </div>
  );
};
