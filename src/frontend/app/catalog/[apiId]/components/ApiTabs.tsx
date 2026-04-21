'use client';

import { type SyntheticEvent } from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';

export type ApiTabValue =
  | 'overview'
  | 'versions'
  | 'specification'
  | 'deployments'
  | 'metadata-quality';

export interface ApiTabsProps {
  value: ApiTabValue;
  onChange: (tab: ApiTabValue) => void;
}

const TAB_OPTIONS: { value: ApiTabValue; label: string }[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'versions', label: 'Versions' },
  { value: 'specification', label: 'Specification' },
  { value: 'deployments', label: 'Deployments' },
  { value: 'metadata-quality', label: 'Metadata Quality' },
];

export default function ApiTabs({ value, onChange }: ApiTabsProps) {
  const handleChange = (_event: SyntheticEvent, newValue: ApiTabValue) => {
    onChange(newValue);
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }} data-testid="api-tabs">
      <Tabs
        value={value}
        onChange={handleChange}
        aria-label="API detail sections"
        variant="scrollable"
        scrollButtons="auto"
      >
        {TAB_OPTIONS.map((tab) => (
          <Tab key={tab.value} label={tab.label} value={tab.value} />
        ))}
      </Tabs>
    </Box>
  );
}
