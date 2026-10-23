import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FileList } from '../src/components/FileList';
import { FileItem } from '../src/types';

describe('FileList Component', () => {
  const mockFiles: FileItem[] = [
    {
      id: 'f-1',
      filename: 'financial_q3.xlsx',
      content_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      size_bytes: 512000,
      sha256: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
      current_version_id: 'v-1',
      current_version_number: 3,
      total_versions: 3,
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T15:00:00Z',
    },
    {
      id: 'f-2',
      filename: 'script.py',
      content_type: 'text/x-python',
      size_bytes: 4096,
      sha256: '9999991234567890abcdef1234567890abcdef1234567890abcdef1234567890',
      current_version_id: 'v-2',
      current_version_number: 1,
      total_versions: 1,
      created_at: '2026-10-23T11:00:00Z',
      updated_at: '2026-10-23T11:00:00Z',
    },
  ];

  it('renders files with name, version, and formatted size', () => {
    render(
      <FileList
        files={mockFiles}
        total={2}
        limit={50}
        offset={0}
        searchQuery=""
        isLoading={false}
        onSearchChange={vi.fn()}
        onPageChange={vi.fn()}
        onDownload={vi.fn()}
        onViewVersions={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.getByText('financial_q3.xlsx')).toBeInTheDocument();
    expect(screen.getByText('v3')).toBeInTheDocument();
    expect(screen.getByText('500.0 KB')).toBeInTheDocument();
    expect(screen.getByText('script.py')).toBeInTheDocument();
  });

  it('triggers search callback when typing in search input', () => {
    const onSearchChange = vi.fn();
    render(
      <FileList
        files={mockFiles}
        total={2}
        limit={50}
        offset={0}
        searchQuery=""
        isLoading={false}
        onSearchChange={onSearchChange}
        onPageChange={vi.fn()}
        onDownload={vi.fn()}
        onViewVersions={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Search by filename/i);
    fireEvent.change(searchInput, { target: { value: 'script' } });

    expect(onSearchChange).toHaveBeenCalledWith('script');
  });

  it('triggers download, versions, and delete action handlers', () => {
    const onDownload = vi.fn();
    const onViewVersions = vi.fn();
    const onDelete = vi.fn();

    render(
      <FileList
        files={mockFiles}
        total={2}
        limit={50}
        offset={0}
        searchQuery=""
        isLoading={false}
        onSearchChange={vi.fn()}
        onPageChange={vi.fn()}
        onDownload={onDownload}
        onViewVersions={onViewVersions}
        onDelete={onDelete}
      />
    );

    const downloadBtn = screen.getByLabelText('Download financial_q3.xlsx');
    fireEvent.click(downloadBtn);
    expect(onDownload).toHaveBeenCalledWith(mockFiles[0]);

    const versionsBtn = screen.getByLabelText('View versions for financial_q3.xlsx');
    fireEvent.click(versionsBtn);
    expect(onViewVersions).toHaveBeenCalledWith(mockFiles[0]);

    const deleteBtn = screen.getByLabelText('Delete financial_q3.xlsx');
    fireEvent.click(deleteBtn);
    expect(onDelete).toHaveBeenCalledWith(mockFiles[0]);
  });
});
