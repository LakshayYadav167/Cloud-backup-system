import React, { useState } from 'react';
import {
  Search,
  Download,
  Trash2,
  History,
  FileText,
  FileCode,
  FileArchive,
  FileSpreadsheet,
  File,
  Copy,
  Check,
} from 'lucide-react';
import { FileItem } from '../types';

interface FileListProps {
  files: FileItem[];
  total: number;
  limit: number;
  offset: number;
  searchQuery: string;
  isLoading: boolean;
  onSearchChange: (query: string) => void;
  onPageChange: (newOffset: number) => void;
  onDownload: (file: FileItem) => void;
  onViewVersions: (file: FileItem) => void;
  onDelete: (file: FileItem) => void;
}

export const FileList: React.FC<FileListProps> = ({
  files,
  total,
  limit,
  offset,
  searchQuery,
  isLoading,
  onSearchChange,
  onPageChange,
  onDownload,
  onViewVersions,
  onDelete,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyHash = (hash: string, id: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getFileIcon = (filename: string, _mime?: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext || '')) {
      return <File className="w-4 h-4 text-purple-600" />;
    }
    if (['zip', 'rar', 'tar', 'gz', '7z'].includes(ext || '')) {
      return <FileArchive className="w-4 h-4 text-amber-600" />;
    }
    if (['js', 'ts', 'tsx', 'py', 'json', 'html', 'css'].includes(ext || '')) {
      return <FileCode className="w-4 h-4 text-emerald-600" />;
    }
    if (['csv', 'xlsx', 'xls'].includes(ext || '')) {
      return <FileSpreadsheet className="w-4 h-4 text-green-600" />;
    }
    return <FileText className="w-4 h-4 text-blue-600" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-soft-sm overflow-hidden">
      {/* Header with Search */}
      <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-semibold text-navy-900">Stored Files</h3>
          <p className="text-xs text-slate-500">
            Active versioned files tracked on local storage
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by filename..."
            className="w-full text-xs pl-9 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 transition"
          />
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/75 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <th className="py-3 px-5">File Name</th>
              <th className="py-3 px-4">Active Version</th>
              <th className="py-3 px-4">Size</th>
              <th className="py-3 px-4">SHA-256 Checksum</th>
              <th className="py-3 px-4">Last Updated</th>
              <th className="py-3 px-5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-navy-800">
            {isLoading ? (
              // Loading Skeleton
              [1, 2, 3, 4].map((i) => (
                <tr key={i} className="animate-pulse">
                  <td className="py-4 px-5">
                    <div className="h-4 bg-slate-200 rounded w-40" />
                  </td>
                  <td className="py-4 px-4">
                    <div className="h-4 bg-slate-100 rounded w-16" />
                  </td>
                  <td className="py-4 px-4">
                    <div className="h-4 bg-slate-100 rounded w-12" />
                  </td>
                  <td className="py-4 px-4">
                    <div className="h-4 bg-slate-100 rounded w-24" />
                  </td>
                  <td className="py-4 px-4">
                    <div className="h-4 bg-slate-100 rounded w-20" />
                  </td>
                  <td className="py-4 px-5 text-right">
                    <div className="h-6 bg-slate-200 rounded w-16 ml-auto" />
                  </td>
                </tr>
              ))
            ) : files.length === 0 ? (
              // Empty State
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
                    <FileText className="w-6 h-6" />
                  </div>
                  <h4 className="mt-3 text-sm font-semibold text-navy-900">
                    {searchQuery ? 'No matching files found' : 'No Files Uploaded Yet'}
                  </h4>
                  <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
                    {searchQuery
                      ? `No file matching "${searchQuery}" was found. Try a different search term.`
                      : 'Upload documents, archives, or code using the upload area above.'}
                  </p>
                </td>
              </tr>
            ) : (
              files.map((file) => (
                <tr
                  key={file.id}
                  className="hover:bg-slate-50/75 transition-colors group"
                >
                  {/* File Name */}
                  <td className="py-3.5 px-5">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center shrink-0">
                        {getFileIcon(file.filename, file.content_type)}
                      </div>
                      <span className="font-semibold text-navy-900 truncate max-w-[200px] sm:max-w-xs" title={file.filename}>
                        {file.filename}
                      </span>
                    </div>
                  </td>

                  {/* Active Version */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center space-x-1.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        v{file.current_version_number}
                      </span>
                      {file.total_versions > 1 && (
                        <span className="text-[10px] text-slate-400">
                          ({file.total_versions} total)
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Size */}
                  <td className="py-3.5 px-4 text-slate-600 font-medium">
                    {formatFileSize(file.size_bytes)}
                  </td>

                  {/* SHA-256 Checksum */}
                  <td className="py-3.5 px-4">
                    <button
                      type="button"
                      onClick={() => copyHash(file.sha256, file.id)}
                      className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-100 hover:bg-slate-200 text-[10px] font-mono text-slate-600 transition"
                      title="Click to copy full SHA-256 checksum"
                    >
                      <span>{file.sha256.substring(0, 10)}...</span>
                      {copiedId === file.id ? (
                        <Check className="w-3 h-3 text-emerald-600" />
                      ) : (
                        <Copy className="w-3 h-3 text-slate-400" />
                      )}
                    </button>
                  </td>

                  {/* Updated Date */}
                  <td className="py-3.5 px-4 text-slate-500 text-[11px]">
                    {new Date(file.updated_at).toLocaleString(undefined, {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </td>

                  {/* Actions */}
                  <td className="py-3.5 px-5 text-right">
                    <div className="flex items-center justify-end space-x-1">
                      {/* Download */}
                      <button
                        type="button"
                        onClick={() => onDownload(file)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 transition"
                        title="Download current version"
                        aria-label={`Download ${file.filename}`}
                      >
                        <Download className="w-4 h-4" />
                      </button>

                      {/* Versions */}
                      <button
                        type="button"
                        onClick={() => onViewVersions(file)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-navy-900 hover:bg-slate-100 transition"
                        title="View version history & restore"
                        aria-label={`View versions for ${file.filename}`}
                      >
                        <History className="w-4 h-4" />
                      </button>

                      {/* Delete */}
                      <button
                        type="button"
                        onClick={() => onDelete(file)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                        title="Delete file"
                        aria-label={`Delete ${file.filename}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {!isLoading && total > 0 && (
        <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing <span className="font-semibold text-navy-900">{Math.min(offset + 1, total)}</span> to{' '}
            <span className="font-semibold text-navy-900">
              {Math.min(offset + limit, total)}
            </span>{' '}
            of <span className="font-semibold text-navy-900">{total}</span> files
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => onPageChange(Math.max(0, offset - limit))}
              className="px-2.5 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>
            <span className="font-medium text-navy-800">
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              disabled={offset + limit >= total}
              onClick={() => onPageChange(offset + limit)}
              className="px-2.5 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
