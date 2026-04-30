'use client';

import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Skeleton from '@mui/material/Skeleton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import DownloadIcon from '@mui/icons-material/Download';
import VisibilityIcon from '@mui/icons-material/Visibility';

import type { BackupSummary } from '@/lib/backup-api';

import BackupStatusChip from './BackupStatusChip';

interface BackupListProps {
  backups: BackupSummary[];
  isLoading: boolean;
  onViewDetails: (backup: BackupSummary) => void;
  onDownload: (backup: BackupSummary) => void;
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function BackupList({
  backups,
  isLoading,
  onViewDetails,
  onDownload,
}: BackupListProps) {
  if (isLoading && backups.length === 0) {
    return (
      <Box>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton
            key={i}
            variant="rectangular"
            height={48}
            sx={{ mb: 1 }}
            data-testid="backup-skeleton"
          />
        ))}
      </Box>
    );
  }

  if (!isLoading && backups.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <Typography variant="body1" color="text.secondary" data-testid="backup-empty">
          No backups available yet. The first backup will appear after the next scheduled run.
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table size="small" aria-label="Backup history" data-testid="backup-table">
        <TableHead>
          <TableRow>
            <TableCell>Backup ID</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Service</TableCell>
            <TableCell align="right">Size</TableCell>
            <TableCell align="right">APIs</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {backups.map((backup) => (
            <TableRow key={backup.backupId} hover data-testid={`backup-row-${backup.backupId}`}>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                  {backup.backupId}
                </Typography>
              </TableCell>
              <TableCell>{formatTimestamp(backup.timestamp)}</TableCell>
              <TableCell>{backup.sourceServiceName}</TableCell>
              <TableCell align="right">{backup.sizeFormatted}</TableCell>
              <TableCell align="right">{backup.counts.apis}</TableCell>
              <TableCell>
                <BackupStatusChip tiers={backup.retentionTiers} status={backup.status} />
              </TableCell>
              <TableCell align="right">
                <Tooltip title="View details">
                  <IconButton
                    size="small"
                    onClick={() => onViewDetails(backup)}
                    aria-label={`View details for ${backup.backupId}`}
                  >
                    <VisibilityIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Download backup ZIP">
                  <IconButton
                    size="small"
                    onClick={() => onDownload(backup)}
                    aria-label={`Download ${backup.backupId}`}
                  >
                    <DownloadIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
