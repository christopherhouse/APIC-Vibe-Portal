'use client';

import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import DownloadIcon from '@mui/icons-material/Download';

import type { BackupSummary } from '@/lib/backup-api';
import BackupStatusChip from './BackupStatusChip';

interface BackupDetailDialogProps {
  open: boolean;
  backup: BackupSummary;
  onClose: () => void;
  onDownload: (backup: BackupSummary) => void;
}

interface FactProps {
  label: string;
  value: React.ReactNode;
}

function Fact({ label, value }: FactProps) {
  return (
    <Stack direction="row" spacing={2} sx={{ justifyContent: 'space-between' }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        {value}
      </Typography>
    </Stack>
  );
}

export default function BackupDetailDialog({
  open,
  backup,
  onClose,
  onDownload,
}: BackupDetailDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'block' }}>
          Backup
        </Typography>
        <Typography variant="h6" component="div" sx={{ fontFamily: 'monospace' }}>
          {backup.backupId}
        </Typography>
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={1.5} data-testid="backup-detail">
          <Fact label="Source service" value={backup.sourceServiceName} />
          <Fact label="Created" value={new Date(backup.timestamp).toLocaleString()} />
          <Fact label="Blob name" value={backup.blobName} />
          <Fact label="Size" value={backup.sizeFormatted} />
          <Fact label="Duration" value={`${backup.durationMs} ms`} />
          <Divider />
          <Typography variant="subtitle2">Catalogue counts</Typography>
          <Fact label="APIs" value={backup.counts.apis} />
          <Fact label="Versions" value={backup.counts.versions} />
          <Fact label="Definitions" value={backup.counts.definitions} />
          <Fact label="Deployments" value={backup.counts.deployments} />
          <Fact label="Environments" value={backup.counts.environments} />
          <Divider />
          <Typography variant="subtitle2">Retention</Typography>
          <BackupStatusChip tiers={backup.retentionTiers} status={backup.status} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={() => onDownload(backup)}
          data-testid="backup-detail-download"
        >
          Download
        </Button>
      </DialogActions>
    </Dialog>
  );
}
