'use client';

import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';

interface BackupStatusChipProps {
  tiers: string[];
  status: string;
}

const TIER_COLOURS: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'info'> = {
  hourly: 'default',
  daily: 'info',
  monthly: 'primary',
  annual: 'secondary',
};

/**
 * Render a row of small chips for a backup's status and retention tiers.
 */
export default function BackupStatusChip({ tiers, status }: BackupStatusChipProps) {
  const isCompleted = status === 'completed';
  return (
    <Stack
      direction="row"
      spacing={0.5}
      useFlexGap
      sx={{ flexWrap: 'wrap' }}
      data-testid="backup-status"
    >
      <Chip
        label={status}
        size="small"
        color={isCompleted ? 'success' : 'error'}
        variant="filled"
      />
      {tiers.map((tier) => (
        <Chip
          key={tier}
          label={tier}
          size="small"
          variant="outlined"
          color={TIER_COLOURS[tier] ?? 'default'}
        />
      ))}
    </Stack>
  );
}
