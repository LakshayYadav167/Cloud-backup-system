import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from '../src/App';
import { api } from '../src/services/api';

// Mock the API service
vi.mock('../src/services/api', () => ({
  api: {
    getHealth: vi.fn(),
    getStorageStats: vi.fn(),
    listFiles: vi.fn(),
    getFile: vi.fn(),
    uploadFile: vi.fn(),
    getFileVersions: vi.fn(),
    downloadFile: vi.fn(),
    restoreFileVersion: vi.fn(),
    deleteFile: vi.fn(),
    triggerBackup: vi.fn(),
    getBackupHistory: vi.fn(),
  },
}));

describe('Cloud Backup System Dashboard Component', () => {
  const mockHealth = {
    status: 'healthy' as const,
    app_name: 'Cloud Backup System API',
    version: '1.0.0',
    environment: 'development',
    storage_provider: 'local',
    database_status: 'connected',
    timestamp: '2026-10-23T23:30:00Z',
  };

  const mockStats = {
    provider: 'local',
    total_files: 2,
    total_versions: 3,
    total_bytes: 2097152,
    total_readable: '2.00 MB',
    quota_bytes: 52428800,
    quota_readable: '50.00 MB',
    quota_percent_used: 4.0,
    base_location: './data/storage',
    last_backup_at: '2026-10-23T22:00:00Z',
  };

  const mockFiles = {
    items: [
      {
        id: 'file-123',
        filename: 'report.pdf',
        content_type: 'application/pdf',
        size_bytes: 1048576,
        sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        current_version_id: 'ver-1',
        current_version_number: 2,
        total_versions: 2,
        created_at: '2026-10-23T20:00:00Z',
        updated_at: '2026-10-23T21:00:00Z',
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  };

  const mockSnapshots = {
    snapshots: [
      {
        id: 'snap-1',
        status: 'COMPLETED' as const,
        snapshot_timestamp: '2026-10-23T22:00:00Z',
        total_files: 1,
        total_bytes: 1048576,
        total_readable: '1.00 MB',
        checksum: 'a1b2c3d4e5f60000000000000000000000000000000000000000000000000000',
        notes: 'Initial test snapshot',
      },
    ],
    total: 1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getHealth).mockResolvedValue(mockHealth);
    vi.mocked(api.getStorageStats).mockResolvedValue(mockStats);
    vi.mocked(api.listFiles).mockResolvedValue(mockFiles);
    vi.mocked(api.getBackupHistory).mockResolvedValue(mockSnapshots);
  });

  it('renders the header title and zero budget guarantee', async () => {
    render(<App />);

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: /Cloud Backup System/i })
      ).toBeInTheDocument();
      expect(screen.getAllByText(/₹0 Budget/i)[0]).toBeInTheDocument();
    });
  });

  it('displays real storage statistics from backend', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('2.00 MB')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // total files
      expect(screen.getByText('Local Disk')).toBeInTheDocument();
    });
  });

  it('renders the file inventory with uploaded files', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('report.pdf')).toBeInTheDocument();
      expect(screen.getByText('v2')).toBeInTheDocument();
    });
  });

  it('switches to Backup Snapshots tab and displays snapshots', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('report.pdf')).toBeInTheDocument();
    });

    const backupsTab = screen.getByRole('button', { name: /Backup Snapshots/i });
    fireEvent.click(backupsTab);

    await waitFor(() => {
      expect(screen.getByText('Initial test snapshot')).toBeInTheDocument();
      expect(screen.getByText('snap-1...')).toBeInTheDocument();
    });
  });

  it('shows error banner when backend is unreachable', async () => {
    vi.mocked(api.getHealth).mockRejectedValue(new Error('Connection refused'));
    vi.mocked(api.getStorageStats).mockRejectedValue(new Error('Connection refused'));

    render(<App />);

    await waitFor(() => {
      expect(
        screen.getByText(/FastAPI Backend Connection Unavailable/i)
      ).toBeInTheDocument();
    });
  });
});
