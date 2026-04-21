'use client';

import { Box, Button, ButtonGroup, Typography } from '@mui/material';
import type { TimeRange } from '@/lib/analytics-api';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

const TIME_RANGE_OPTIONS: { label: string; value: TimeRange }[] = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' },
  { label: 'Last year', value: '1y' },
];

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }} data-testid="time-range-selector">
      <Typography variant="body2" color="text.secondary">
        Time range:
      </Typography>
      <ButtonGroup size="small" variant="outlined" aria-label="time range selection">
        {TIME_RANGE_OPTIONS.map((option) => (
          <Button
            key={option.value}
            variant={value === option.value ? 'contained' : 'outlined'}
            onClick={() => onChange(option.value)}
            data-testid={`time-range-${option.value}`}
          >
            {option.label}
          </Button>
        ))}
      </ButtonGroup>
    </Box>
  );
}
