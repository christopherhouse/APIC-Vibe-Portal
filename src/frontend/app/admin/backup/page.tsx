'use client';

/**
 * Admin — API Center Backup management page.
 *
 * Visible only to users with the `Portal.Admin` role. Lists recent backups
 * produced by the backup container job, surfaces metadata (size, counts,
 * retention tiers), and allows admins to download a backup ZIP via a
 * short-lived SAS URL.
 */

import { useCallback, useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import Snackbar from '@mui/material/Snackbar';
import Button from '@mui/material/Button';
import RefreshIcon from '@mui/icons-material/Refresh';
import BlockIcon from '@mui/icons-material/Block';

import { useAuth } from '@/lib/auth/use-auth';
import { fetchBackups, fetchBackupDownload, type BackupSummary } from '@/lib/backup-api';

import BackupList from './components/BackupList';
import BackupDetailDialog from './components/BackupDetailDialog';

const ADMIN_ROLE = 'Portal.Admin';

export default function BackupAdminPage() {
  const { user, isAuthenticated } = useAuth();
  const isAdmin = Boolean(user?.roles.includes(ADMIN_ROLE));

  const [backups, setBackups] = useState<BackupSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [continuationToken, setContinuationToken] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<BackupSummary | null>(null);

  const [snackbar, setSnackbar] = useState<{
    message: string;
    severity: 'success' | 'error' | 'info';
  } | null>(null);

  const loadBackups = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await fetchBackups();
      setBackups(response.data);
      setContinuationToken(response.pagination.continuationToken);
      setHasMore(response.pagination.hasMore);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load backups.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (!continuationToken || isLoadingMore) return;
    setIsLoadingMore(true);
    setLoadError(null);
    try {
      const response = await fetchBackups(50, continuationToken);
      setBackups((prev) => [...prev, ...response.data]);
      setContinuationToken(response.pagination.continuationToken);
      setHasMore(response.pagination.hasMore);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load more backups.');
    } finally {
      setIsLoadingMore(false);
    }
  }, [continuationToken, isLoadingMore]);

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      void loadBackups();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated, isAdmin, loadBackups]);

  const handleViewDetails = (backup: BackupSummary) => {
    setSelectedBackup(backup);
    setDetailOpen(true);
  };

  const handleDownload = async (backup: BackupSummary) => {
    try {
      setSnackbar({ message: 'Generating download link…', severity: 'info' });
      const result = await fetchBackupDownload(backup.backupId);
      // Trigger the download in a new tab — the SAS URL is short-lived (1h).
      window.open(result.downloadUrl, '_blank', 'noopener,noreferrer');
      setSnackbar({
        message: `Download started for ${backup.backupId}.`,
        severity: 'success',
      });
    } catch (err) {
      setSnackbar({
        message: err instanceof Error ? err.message : 'Failed to start download.',
        severity: 'error',
      });
    }
  };

  if (!isAdmin && !isLoading) {
    return (
      <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
        <BlockIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Access Denied
        </Typography>
        <Typography variant="body1" color="text.secondary">
          You need the <strong>Portal.Admin</strong> role to view backups.
        </Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ mb: 3, alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
      >
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            API Center Backups
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Browse hourly backups of the API Center catalogue. Backups are produced by the scheduled
            backup job and retained according to a grandfather-father-son policy.
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => void loadBackups()}
          disabled={isLoading}
          data-testid="backup-refresh"
        >
          Refresh
        </Button>
      </Stack>

      {loadError && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="backup-load-error">
          {loadError}
        </Alert>
      )}

      <BackupList
        backups={backups}
        isLoading={isLoading}
        onViewDetails={handleViewDetails}
        onDownload={(b) => void handleDownload(b)}
      />

      {hasMore && !isLoading && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
          <Button
            variant="outlined"
            onClick={() => void loadMore()}
            disabled={isLoadingMore}
            data-testid="backup-load-more"
          >
            {isLoadingMore ? 'Loading…' : 'Load more'}
          </Button>
        </Box>
      )}

      {selectedBackup && (
        <BackupDetailDialog
          open={detailOpen}
          backup={selectedBackup}
          onClose={() => setDetailOpen(false)}
          onDownload={(b) => void handleDownload(b)}
        />
      )}

      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={4000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {snackbar ? (
          <Alert
            onClose={() => setSnackbar(null)}
            severity={snackbar.severity}
            variant="filled"
            data-testid="backup-snackbar"
          >
            {snackbar.message}
          </Alert>
        ) : (
          <span />
        )}
      </Snackbar>
    </Container>
  );
}
