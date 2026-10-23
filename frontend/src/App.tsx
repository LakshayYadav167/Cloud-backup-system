import React, { useState } from 'react';
import {
  HardDrive,
  UploadCloud,
  FileText,
  Clock,
  ShieldCheck,
  Server,
  Layers,
  Sparkles,
  ExternalLink,
} from 'lucide-react';

export const App: React.FC = () => {
  const [selectedNav, setSelectedNav] = useState<'dashboard' | 'files' | 'backups'>('dashboard');

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-navy-900">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-soft-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500 flex items-center justify-center text-white shadow-sm">
                <HardDrive className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight text-navy-900">
                  Cloud Backup System
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  Self-Hosted &amp; Zero-Cost Architecture (₹0 Budget)
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                Phase 1 Foundation Ready
              </span>
              <span className="hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-navy-700 border border-slate-200">
                <Server className="w-3.5 h-3.5 mr-1" />
                FastAPI + SQLite
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Foundation Welcome Banner */}
        <div className="rounded-xl border border-emerald-100 bg-gradient-to-r from-emerald-50 via-white to-slate-50 p-6 shadow-soft-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 text-emerald-800 font-semibold text-sm">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>Phase 1 Milestone Complete</span>
              </div>
              <h2 className="text-xl font-bold text-navy-900">
                Workspace Foundation &amp; Technical Baseline Established
              </h2>
              <p className="text-sm text-slate-600 max-w-2xl">
                Monorepo architecture configured with React + Vite + Tailwind, Python + FastAPI,
                an abstract <code className="text-emerald-700 bg-emerald-100/60 px-1 py-0.5 rounded font-mono text-xs">StorageProvider</code> layer,
                and local SQLite schema. Ready for Phase 2 core storage engine integration.
              </p>
            </div>
            <div className="flex items-center space-x-3 self-start md:self-center">
              <a
                href="http://127.0.0.1:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-white text-navy-800 border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition shadow-soft-sm"
              >
                <span>API Swagger Docs</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <a
                href="http://127.0.0.1:8000/api/v1/health"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition shadow-soft-sm"
              >
                <span>Check API Health</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Storage Statistics Cards Grid */}
        <section aria-labelledby="stats-heading">
          <h2 id="stats-heading" className="sr-only">Storage Overview Statistics</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Storage</span>
                <div className="w-8 h-8 rounded-md bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <HardDrive className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-navy-900">0.00 MB</div>
                <div className="mt-1 text-xs text-slate-500">Local Filesystem (Disk Quota: 50 MB)</div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Tracked Files</span>
                <div className="w-8 h-8 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center">
                  <FileText className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-navy-900">0 Files</div>
                <div className="mt-1 text-xs text-slate-500">SQLite Metadata Registry</div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Backup Snapshots</span>
                <div className="w-8 h-8 rounded-md bg-purple-50 text-purple-600 flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-navy-900">0 Snapshots</div>
                <div className="mt-1 text-xs text-slate-500">Ready for automated backups</div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Storage Driver</span>
                <div className="w-8 h-8 rounded-md bg-amber-50 text-amber-600 flex items-center justify-center">
                  <Layers className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-navy-900">Local Disk</div>
                <div className="mt-1 text-xs text-slate-500">Abstract StorageProvider (Pluggable)</div>
              </div>
            </div>
          </div>
        </section>

        {/* Primary Functional Sections Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* File Upload Area */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-soft-sm">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <h3 className="font-semibold text-navy-900 flex items-center space-x-2">
                  <UploadCloud className="w-5 h-5 text-emerald-600" />
                  <span>Upload Files</span>
                </h3>
                <span className="text-xs font-medium text-slate-400">Max 50 MB</span>
              </div>

              {/* Upload Drop Zone Blueprint */}
              <div className="mt-5 border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-emerald-400 hover:bg-emerald-50/20 transition-all cursor-pointer group">
                <div className="mx-auto w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <h4 className="mt-3 text-sm font-semibold text-navy-900">
                  Select files or drag &amp; drop
                </h4>
                <p className="mt-1 text-xs text-slate-500">
                  Supports documents, archives, images &amp; logs
                </p>
                <div className="mt-4">
                  <button
                    type="button"
                    className="inline-flex items-center px-4 py-2 rounded-lg text-xs font-semibold bg-navy-900 text-white hover:bg-navy-800 transition shadow-sm"
                  >
                    Browse Files
                  </button>
                </div>
              </div>

              <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
                <div className="font-medium text-navy-800">Storage Pipeline Overview:</div>
                <ul className="list-disc list-inside space-y-0.5 text-slate-500">
                  <li>Client streams file to FastAPI backend</li>
                  <li>SHA-256 hash computed for integrity</li>
                  <li>UUID v4 filename written to disk</li>
                  <li>Metadata stored in SQLite database</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Files Inventory & Backup History Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* View Selector Tabs */}
            <div className="flex space-x-2 border-b border-slate-200 pb-2">
              <button
                type="button"
                onClick={() => setSelectedNav('dashboard')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  selectedNav === 'dashboard'
                    ? 'bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200'
                    : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
                }`}
              >
                File Inventory
              </button>
              <button
                type="button"
                onClick={() => setSelectedNav('backups')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  selectedNav === 'backups'
                    ? 'bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200'
                    : 'text-slate-600 hover:text-navy-900 hover:bg-slate-100'
                }`}
              >
                Backup History &amp; Snapshots
              </button>
            </div>

            {/* Inventory Container */}
            {selectedNav === 'dashboard' && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-soft-sm overflow-hidden">
                <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-navy-900">Stored Files</h3>
                    <p className="text-xs text-slate-500">All files stored on local filesystem storage driver</p>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-600">
                    0 Items
                  </span>
                </div>

                <div className="p-12 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-medium text-navy-900">No Files Uploaded Yet</div>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    The filesystem storage and SQLite repository are primed. In Phase 2,
                    file uploads via the REST API will populate this inventory in real-time.
                  </p>
                </div>
              </div>
            )}

            {/* Backup History Container */}
            {selectedNav === 'backups' && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-soft-sm overflow-hidden">
                <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-navy-900">Backup Snapshots</h3>
                    <p className="text-xs text-slate-500">Immutable snapshot records and verification checksums</p>
                  </div>
                  <button
                    type="button"
                    disabled
                    className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-800 opacity-60 cursor-not-allowed"
                    title="Enabled in Phase 2"
                  >
                    Trigger Backup Snapshot
                  </button>
                </div>

                <div className="p-12 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
                    <Clock className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-medium text-navy-900">No Snapshots Generated Yet</div>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    Automated snapshots and point-in-time recovery tracking will be wired to SQLite in Phase 2.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div>
            <span className="font-semibold text-navy-900">Cloud Backup System</span> &mdash; College Submission Project
          </div>
          <div className="flex items-center space-x-4">
            <span>Stack: React + Vite + FastAPI + SQLite</span>
            <span>&bull;</span>
            <span className="text-emerald-600 font-medium">₹0 Zero Budget Guarantee</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
