import React from 'react';
import { HardDrive, Server, RefreshCw, ExternalLink } from 'lucide-react';
import { HealthResponse, StorageStats } from '../types';

interface NavbarProps {
  health: HealthResponse | null;
  storageStats: StorageStats | null;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  storageStats,
  isRefreshing,
  onRefresh,
}) => {
  const isHealthy = health?.status === 'healthy';
  const provider = storageStats?.provider || health?.storage_provider || 'local';

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-soft-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center text-white shadow-sm">
              <HardDrive className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-navy-900">
                  Cloud Backup System
                </h1>
                <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Self-Hosted
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Self-Hosted Enterprise Cloud Storage &amp; Automated Versioning
              </p>
            </div>
          </div>

          {/* Indicators & Actions */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Storage Provider Badge */}
            <span className="hidden sm:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-navy-700 border border-slate-200">
              <Server className="w-3.5 h-3.5 mr-1 text-slate-500" />
              <span>{provider.toUpperCase()} Provider</span>
            </span>

            {/* Health Status Indicator */}
            <span
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${
                isHealthy
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border-rose-200'
              }`}
              title={`API Status: ${health?.status || 'connecting'}`}
            >
              <span
                className={`w-2 h-2 rounded-full mr-1.5 ${
                  isHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                }`}
              />
              <span className="capitalize">{health?.status || 'Connecting...'}</span>
            </span>

            {/* Refresh Button */}
            <button
              type="button"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-navy-900 hover:bg-slate-50 transition shadow-soft-sm"
              title="Refresh Dashboard Data"
              aria-label="Refresh Dashboard Data"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-600' : ''}`} />
            </button>

            {/* API Docs Link */}
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="hidden lg:inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-navy-900 text-white hover:bg-navy-800 transition shadow-sm"
            >
              <span>Swagger API</span>
              <ExternalLink className="w-3 h-3 ml-0.5 opacity-80" />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
};
