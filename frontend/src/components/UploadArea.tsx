import React, { useRef, useState } from 'react';
import { UploadCloud, File, AlertCircle, X } from 'lucide-react';
import { api } from '../services/api';
import { FileUploadResponse } from '../types';

interface UploadAreaProps {
  maxSizeMb?: number;
  onUploadSuccess: (response: FileUploadResponse) => void;
  onUploadError: (errorMessage: string) => void;
}

const RESERVED_NAMES = [
  'CON', 'PRN', 'AUX', 'NUL',
  'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
  'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
];

export const UploadArea: React.FC<UploadAreaProps> = ({
  maxSizeMb = 50,
  onUploadSuccess,
  onUploadError,
}) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [versionNotes, setVersionNotes] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [clientError, setClientError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!file.name || !file.name.trim()) {
      return 'Filename cannot be empty.';
    }

    const stem = file.name.split('.')[0].toUpperCase();
    if (RESERVED_NAMES.includes(stem)) {
      return `Filename '${file.name}' matches a reserved Windows device name (${stem}).`;
    }

    const maxBytes = maxSizeMb * 1024 * 1024;
    if (file.size > maxBytes) {
      return `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds maximum upload limit of ${maxSizeMb} MB.`;
    }

    return null;
  };

  const handleFileSelection = (file: File) => {
    const error = validateFile(file);
    if (error) {
      setClientError(error);
      setSelectedFile(null);
    } else {
      setClientError(null);
      setSelectedFile(file);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelection(e.target.files[0]);
    }
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setVersionNotes('');
    setClientError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setClientError(null);

    try {
      const response = await api.uploadFile(selectedFile, versionNotes);
      onUploadSuccess(response);
      clearSelection();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed unexpectedly';
      setClientError(msg);
      onUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-soft-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <h3 className="font-semibold text-navy-900 flex items-center space-x-2">
          <UploadCloud className="w-5 h-5 text-emerald-600" />
          <span>Upload File</span>
        </h3>
        <span className="text-xs font-medium text-slate-400">Limit: {maxSizeMb} MB</span>
      </div>

      <form onSubmit={handleUpload} className="mt-5 space-y-4">
        {/* Hidden Native Input */}
        <input
          ref={fileInputRef}
          type="file"
          id="file-upload-input"
          aria-label="Select file to upload"
          data-testid="file-upload-input"
          className="hidden"
          onChange={handleChange}
          disabled={isUploading}
        />

        {/* Drag & Drop Zone */}
        {!selectedFile ? (
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer group ${
              dragActive
                ? 'border-emerald-500 bg-emerald-50/50 scale-[1.01]'
                : 'border-slate-200 hover:border-emerald-400 hover:bg-emerald-50/20'
            }`}
          >
            <div className="mx-auto w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
              <UploadCloud className="w-6 h-6" />
            </div>
            <h4 className="mt-3 text-sm font-semibold text-navy-900">
              Select files or drag &amp; drop
            </h4>
            <p className="mt-1 text-xs text-slate-500">
              Uploading a modified file automatically increments its version
            </p>
            <div className="mt-4">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="inline-flex items-center px-4 py-2 rounded-lg text-xs font-semibold bg-navy-900 text-white hover:bg-navy-800 transition shadow-sm"
              >
                Browse Files
              </button>
            </div>
          </div>
        ) : (
          /* Selected File Preview Box */
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3 overflow-hidden">
                <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                  <File className="w-5 h-5" />
                </div>
                <div className="truncate">
                  <p className="text-sm font-semibold text-navy-900 truncate" title={selectedFile.name}>
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatFileSize(selectedFile.size)} &bull; {selectedFile.type || 'Binary'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={clearSelection}
                disabled={isUploading}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition"
                title="Remove selection"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Version Notes Input */}
            <div>
              <label htmlFor="version-notes-input" className="block text-xs font-medium text-navy-800 mb-1">
                Version Summary / Notes (Optional)
              </label>
              <input
                id="version-notes-input"
                type="text"
                value={versionNotes}
                onChange={(e) => setVersionNotes(e.target.value)}
                placeholder="e.g. Added section 4, fixed typo"
                disabled={isUploading}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end space-x-2 pt-1">
              <button
                type="button"
                onClick={clearSelection}
                disabled={isUploading}
                className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 hover:bg-slate-100 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isUploading}
                className={`inline-flex items-center px-4 py-1.5 text-xs font-semibold rounded-lg text-white bg-emerald-600 hover:bg-emerald-700 transition shadow-sm ${
                  isUploading ? 'opacity-70 cursor-not-allowed' : ''
                }`}
              >
                {isUploading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <span>Uploading...</span>
                  </>
                ) : (
                  <span>Upload Now</span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Validation Error Message */}
        {clientError && (
          <div className="flex items-start space-x-2 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{clientError}</span>
          </div>
        )}

        {/* Storage Pipeline Overview Box */}
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1">
          <div className="font-semibold text-navy-800">Automatic Versioning Pipeline:</div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-500">
            <li>SHA-256 computed on upload for file integrity</li>
            <li>Stored under immutable internal keys on disk</li>
            <li>Existing files automatically create incremented versions</li>
          </ul>
        </div>
      </form>
    </div>
  );
};
