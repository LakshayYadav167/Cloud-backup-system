import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BackupSnapshots } from '../src/components/BackupSnapshots';
import { api } from '../src/services/api';

vi.mock('../src/services/api', () => ({
  api: {
    exportArchive: vi.fn(),
    verifyArchive: vi.fn(),
    restoreArchive: vi.fn(),
  },
}));

describe('BackupSnapshots - Portable Archives (Phase 7)', () => {
  const mockSnapshots = [
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
  ];

  const defaultProps = {
    snapshots: mockSnapshots,
    total: 1,
    isLoading: false,
    onTriggerBackup: vi.fn(),
    onRefresh: vi.fn(),
    onArchiveRestored: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders snapshot history tab by default', () => {
    render(<BackupSnapshots {...defaultProps} />);
    expect(screen.getByText('Point-in-Time Snapshots (1)')).toBeInTheDocument();
    expect(screen.getByText('Initial test snapshot')).toBeInTheDocument();
  });

  it('switches to Portable Archives tab and renders all 3 operation cards', () => {
    render(<BackupSnapshots {...defaultProps} />);
    const archivesTab = screen.getByRole('button', { name: /Portable Archives/i });
    fireEvent.click(archivesTab);

    expect(screen.getByText(/Self-Contained, Independently Restorable Backup Archives/i)).toBeInTheDocument();
    expect(screen.getByText(/1\. Export Archive/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Verify Archive/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Restore Archive/i)).toBeInTheDocument();
  });

  it('handles export archive download trigger', async () => {
    vi.mocked(api.exportArchive).mockResolvedValue(undefined);
    render(<BackupSnapshots {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Portable Archives/i }));

    const exportBtn = screen.getByRole('button', { name: /Export & Download/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(api.exportArchive).toHaveBeenCalledTimes(1);
    });
  });

  it('handles archive verification and displays validation details', async () => {
    vi.mocked(api.verifyArchive).mockResolvedValue({
      valid: true,
      format_version: '1.0.0',
      generator: 'CloudBackupSystem/1.0.0',
      exported_at: '2026-10-23T23:00:00Z',
      total_files: 3,
      total_versions: 5,
      total_bytes: 4096,
      total_readable: '4.00 KB',
      errors: [],
      warnings: [],
    });

    render(<BackupSnapshots {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /Portable Archives/i }));

    const file = new File(['mock zip content'], 'backup.zip', { type: 'application/zip' });
    const verifyInput = screen.getByLabelText(/Select Archive to Verify/i);
    fireEvent.change(verifyInput, { target: { files: [file] } });

    const verifyBtn = screen.getByRole('button', { name: /Verify Archive/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(api.verifyArchive).toHaveBeenCalledWith(file);
      expect(screen.getByText(/Verification Passed \(Valid\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Files: 3/i)).toBeInTheDocument();
      expect(screen.getByText(/Versions: 5/i)).toBeInTheDocument();
    });
  });

  it('handles archive restore with conflict strategy and triggers callback', async () => {
    vi.mocked(api.restoreArchive).mockResolvedValue({
      success: true,
      message: 'Successfully imported 2 files and 3 versions',
      conflict_strategy: 'rename',
      imported_files_count: 2,
      imported_versions_count: 3,
      skipped_files_count: 0,
      details: ['Imported file A', 'Imported file B'],
    });

    render(<BackupSnapshots {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /Portable Archives/i }));

    const file = new File(['mock zip content'], 'backup.zip', { type: 'application/zip' });
    const restoreInput = screen.getByLabelText(/Select Archive to Restore/i);
    fireEvent.change(restoreInput, { target: { files: [file] } });

    // Confirm checkbox
    const confirmCheck = screen.getByLabelText(/I confirm importing this archive/i);
    fireEvent.click(confirmCheck);

    const restoreBtn = screen.getByRole('button', { name: /Execute Restore/i });
    fireEvent.click(restoreBtn);

    await waitFor(() => {
      expect(api.restoreArchive).toHaveBeenCalledWith(file, 'rename');
      expect(screen.getByText(/Successfully imported 2 files and 3 versions/i)).toBeInTheDocument();
      expect(defaultProps.onArchiveRestored).toHaveBeenCalledTimes(1);
    });
  });
});
