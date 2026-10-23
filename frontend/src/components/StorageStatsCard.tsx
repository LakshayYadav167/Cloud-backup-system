import React from 'react';
import { HardDrive, FileText, Layers, Clock } from 'lucide-react';
import { StorageStats } from '../types';

interface StorageStatsCardProps {
  stats: StorageStats | null;
  isLoading: boolean;
}

export const StorageStatsCard: React.FC<StorageStatsCardProps> = ({ stats, isLoading }) => {
  if (isLoading && !stats) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-5 h-32 space-y-3">
            <div className="h-4 bg-slate-200 rounded w-1/3" />
            <div className="h-7 bg-slate-200 rounded w-1/2" />
            <div className="h-3 bg-slate-100 rounded w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  const percentUsed = stats?.quota_percent_used ?? 0;
  const isHighUsage = percentUsed > 80;

  return (
    <section aria-labelledby="stats-heading">
      <h2 id="stats-heading" className="sr-only">Storage Overview Statistics</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Storage Capacity */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Total Storage
            </span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <HardDrive className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-navy-900">
                {stats?.total_readable || '0 B'}
              </span>
              <span className="text-xs text-slate-400">/ {stats?.quota_readable || '50 MB'}</span>
            </div>
            {/* Progress Bar */}
            <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  isHighUsage ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, percentUsed))}%` }}
              />
            </div>
            <div className="mt-1 flex justify-between text-[11px] text-slate-500">
              <span>{percentUsed}% Quota Used</span>
              <span className="font-mono text-[10px]">{stats?.base_location || './data/storage'}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Tracked Files */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Tracked Files
            </span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-navy-900">
              {stats?.total_files ?? 0}
              <span className="text-sm font-normal text-slate-500 ml-1">Files</span>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              <span className="font-semibold text-navy-800">{stats?.total_versions ?? 0}</span> total backup versions stored
            </div>
          </div>
        </div>

        {/* Card 3: Backup Snapshots */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Latest Backup
            </span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-sm font-bold text-navy-900 truncate" title={stats?.last_backup_at || 'Never'}>
              {stats?.last_backup_at
                ? new Date(stats.last_backup_at).toLocaleString(undefined, {
                    dateStyle: 'short',
                    timeStyle: 'short',
                  })
                : 'No Snapshots Yet'}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Point-in-time disaster recovery snapshots
            </div>
          </div>
        </div>

        {/* Card 4: Active Storage Driver */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-soft-sm hover:shadow-soft-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Storage Engine
            </span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-navy-900 capitalize">
              {stats?.provider === 's3' ? 'S3 / MinIO' : 'Local Disk'}
            </div>
            <div className="mt-2 text-xs text-slate-500 flex items-center space-x-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>Pluggable StorageProvider ABC</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
