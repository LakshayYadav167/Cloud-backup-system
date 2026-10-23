import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../src/App';

describe('Cloud Backup System Dashboard Shell', () => {
  it('renders the project title and zero budget guarantee', () => {
    render(<App />);
    expect(screen.getByText('Cloud Backup System')).toBeInTheDocument();
    expect(screen.getByText(/₹0 Budget/i)).toBeInTheDocument();
  });

  it('renders the storage metrics cards', () => {
    render(<App />);
    expect(screen.getByText('Total Storage')).toBeInTheDocument();
    expect(screen.getByText('Tracked Files')).toBeInTheDocument();
    expect(screen.getByText('Backup Snapshots')).toBeInTheDocument();
    expect(screen.getByText('Storage Driver')).toBeInTheDocument();
  });

  it('renders the file upload area blueprint', () => {
    render(<App />);
    expect(screen.getByText('Upload Files')).toBeInTheDocument();
    expect(screen.getByText('Browse Files')).toBeInTheDocument();
  });
});
