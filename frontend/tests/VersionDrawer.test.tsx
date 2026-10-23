import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VersionDrawer } from '../src/components/VersionDrawer';
import { api } from '../src/services/api';
import { FileItem, FileVersionSummary } from '../src/types';

vi.mock('../src/services/api', () => ({
  api: {
    getFileVersions: vi.fn(),
  },
}));

describe('VersionDrawer Component', () => {
  const mockFile: FileItem = {
    id: 'file-doc',
    filename: 'project_notes.txt',
    content_type: 'text/plain',
    size_bytes: 2048,
    sha256: 'sha-256-current',
    current_version_id: 'v-2',
    current_version_number: 2,
    total_versions: 2,
    created_at: '2026-10-23T10:00:00Z',
    updated_at: '2026-10-23T12:00:00Z',
  };

  const mockVersions: FileVersionSummary[] = [
    {
      id: 'v-2',
      file_id: 'file-doc',
      version_number: 2,
      size_bytes: 2048,
      sha256: 'hash-v2',
      content_type: 'text/plain',
      change_summary: 'Updated architecture section',
      created_at: '2026-10-23T12:00:00Z',
      is_current: true,
    },
    {
      id: 'v-1',
      file_id: 'file-doc',
      version_number: 1,
      size_bytes: 1024,
      sha256: 'hash-v1',
      content_type: 'text/plain',
      change_summary: 'Initial draft',
      created_at: '2026-10-23T10:00:00Z',
      is_current: false,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getFileVersions).mockResolvedValue(mockVersions);
  });

  it('fetches and renders all historical versions', async () => {
    render(
      <VersionDrawer
        file={mockFile}
        onClose={vi.fn()}
        onRestoreRequest={vi.fn()}
        onDownloadVersion={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('project_notes.txt')).toBeInTheDocument();
      expect(screen.getByText('Version 2')).toBeInTheDocument();
      expect(screen.getByText('Version 1')).toBeInTheDocument();
      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('"Updated architecture section"')).toBeInTheDocument();
      expect(screen.getByText('"Initial draft"')).toBeInTheDocument();
    });
  });

  it('triggers download version and restore handlers', async () => {
    const onDownloadVersion = vi.fn();
    const onRestoreRequest = vi.fn();

    render(
      <VersionDrawer
        file={mockFile}
        onClose={vi.fn()}
        onRestoreRequest={onRestoreRequest}
        onDownloadVersion={onDownloadVersion}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });

    // The older version (Version 1) has a Restore button
    const restoreBtn = screen.getByRole('button', { name: /Restore/i });
    fireEvent.click(restoreBtn);

    expect(onRestoreRequest).toHaveBeenCalledWith(mockFile, mockVersions[1]);

    // Click Download on Version 1
    const downloadBtns = screen.getAllByRole('button', { name: /Download/i });
    fireEvent.click(downloadBtns[1]); // second version download button

    expect(onDownloadVersion).toHaveBeenCalledWith(mockFile, 'v-1');
  });
});
