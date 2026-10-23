import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { UploadArea } from '../src/components/UploadArea';
import { api } from '../src/services/api';

vi.mock('../src/services/api', () => ({
  api: {
    uploadFile: vi.fn(),
  },
}));

describe('UploadArea Component', () => {
  const onUploadSuccess = vi.fn();
  const onUploadError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders upload drop zone and browse button', () => {
    render(
      <UploadArea
        onUploadSuccess={onUploadSuccess}
        onUploadError={onUploadError}
      />
    );

    expect(screen.getByText(/Select files or drag & drop/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Browse Files/i })).toBeInTheDocument();
  });

  it('rejects reserved Windows device names', async () => {
    render(
      <UploadArea
        onUploadSuccess={onUploadSuccess}
        onUploadError={onUploadError}
      />
    );

    const file = new File(['dummy content'], 'CON.txt', { type: 'text/plain' });
    const input = screen.getByTestId('file-upload-input') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/matches a reserved Windows device name/i)).toBeInTheDocument();
    });
  });

  it('rejects files exceeding max size limit', async () => {
    render(
      <UploadArea
        maxSizeMb={1}
        onUploadSuccess={onUploadSuccess}
        onUploadError={onUploadError}
      />
    );

    // Create a 2 MB file
    const largeContent = new Uint8Array(2 * 1024 * 1024);
    const file = new File([largeContent], 'heavy.bin', { type: 'application/octet-stream' });
    const input = screen.getByTestId('file-upload-input') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/exceeds maximum upload limit of 1 MB/i)).toBeInTheDocument();
    });
  });

  it('successfully selects and uploads a valid file', async () => {
    const mockResponse = {
      file: {
        id: 'new-id',
        filename: 'valid.txt',
        content_type: 'text/plain',
        size_bytes: 12,
        sha256: 'checksum-123',
        current_version_number: 1,
        total_versions: 1,
        created_at: '2026-10-23T23:00:00Z',
        updated_at: '2026-10-23T23:00:00Z',
      },
      version: {
        id: 'v-1',
        file_id: 'new-id',
        version_number: 1,
        size_bytes: 12,
        sha256: 'checksum-123',
        content_type: 'text/plain',
        change_summary: 'Initial upload',
        created_at: '2026-10-23T23:00:00Z',
        is_current: true,
      },
      message: "File 'valid.txt' uploaded successfully.",
    };

    vi.mocked(api.uploadFile).mockResolvedValue(mockResponse);

    render(
      <UploadArea
        onUploadSuccess={onUploadSuccess}
        onUploadError={onUploadError}
      />
    );

    const file = new File(['valid content'], 'valid.txt', { type: 'text/plain' });
    const input = screen.getByTestId('file-upload-input') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('valid.txt')).toBeInTheDocument();
    });

    // Enter optional summary
    const notesInput = screen.getByPlaceholderText(/e\.g\. Added section 4/i);
    fireEvent.change(notesInput, { target: { value: 'First test version' } });

    // Click upload
    const uploadBtn = screen.getByRole('button', { name: /Upload Now/i });
    fireEvent.click(uploadBtn);

    await waitFor(() => {
      expect(api.uploadFile).toHaveBeenCalledWith(file, 'First test version');
      expect(onUploadSuccess).toHaveBeenCalledWith(mockResponse);
    });
  });
});
