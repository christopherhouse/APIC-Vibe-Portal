import React from 'react';
import { render, screen, waitFor, fireEvent } from '../../../../__tests__/test-utils';
import '@testing-library/jest-dom';

const mockUseAuth = jest.fn();
jest.mock('@/lib/auth/use-auth', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockFetchBackups = jest.fn();
const mockFetchBackupDownload = jest.fn();
jest.mock('@/lib/backup-api', () => ({
  fetchBackups: (...args: unknown[]) => mockFetchBackups(...args),
  fetchBackupDownload: (...args: unknown[]) => mockFetchBackupDownload(...args),
}));

import BackupAdminPage from '../page';

const adminUser = {
  isAuthenticated: true,
  user: { name: 'Admin', email: 'a@x.com', id: 'u2', roles: ['Portal.Admin'] },
};
const regularUser = {
  isAuthenticated: true,
  user: { name: 'Dev', email: 'd@x.com', id: 'u1', roles: ['Portal.User'] },
};

const sampleBackup = {
  backupId: 'apic-backup-2026-04-28T12-00-00Z',
  sourceServiceName: 'apic-test',
  timestamp: '2026-04-28T12:00:00Z',
  blobName: 'apic-backup-2026-04-28T12-00-00Z.zip',
  sizeBytes: 4096,
  sizeFormatted: '4.0 KB',
  counts: { apis: 2, versions: 2, definitions: 2, deployments: 2, environments: 1 },
  retentionTiers: ['hourly', 'daily'],
  status: 'completed',
  durationMs: 1200,
};

describe('BackupAdminPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows access denied for non-admin users', async () => {
    mockUseAuth.mockReturnValue(regularUser);
    render(<BackupAdminPage />);
    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument();
    });
  });

  it('renders the page heading and refreshes for admins', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchBackups.mockResolvedValue({ items: [sampleBackup], count: 1 });
    render(<BackupAdminPage />);
    await waitFor(() => {
      expect(screen.getByText('API Center Backups')).toBeInTheDocument();
    });
    expect(await screen.findByTestId(`backup-row-${sampleBackup.backupId}`)).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('backup-refresh'));
    await waitFor(() => expect(mockFetchBackups).toHaveBeenCalledTimes(2));
  });

  it('shows the empty state when no backups exist', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchBackups.mockResolvedValue({ items: [], count: 0 });
    render(<BackupAdminPage />);
    expect(await screen.findByTestId('backup-empty')).toBeInTheDocument();
  });

  it('triggers a download via window.open when the action is invoked', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchBackups.mockResolvedValue({ items: [sampleBackup], count: 1 });
    mockFetchBackupDownload.mockResolvedValue({
      backupId: sampleBackup.backupId,
      downloadUrl: 'https://fake.blob/backup.zip?sas=token',
      expiresAt: '2026-04-28T13:00:00Z',
    });
    const openSpy = jest.spyOn(window, 'open').mockReturnValue(null);
    try {
      render(<BackupAdminPage />);
      const downloadBtn = await screen.findByLabelText(`Download ${sampleBackup.backupId}`);
      fireEvent.click(downloadBtn);
      await waitFor(() =>
        expect(mockFetchBackupDownload).toHaveBeenCalledWith(sampleBackup.backupId)
      );
      await waitFor(() =>
        expect(openSpy).toHaveBeenCalledWith(
          'https://fake.blob/backup.zip?sas=token',
          '_blank',
          'noopener,noreferrer'
        )
      );
    } finally {
      openSpy.mockRestore();
    }
  });

  it('surfaces load errors', async () => {
    mockUseAuth.mockReturnValue(adminUser);
    mockFetchBackups.mockRejectedValue(new Error('boom'));
    render(<BackupAdminPage />);
    expect(await screen.findByTestId('backup-load-error')).toHaveTextContent('boom');
  });
});
