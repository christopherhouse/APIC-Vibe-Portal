'use client';

import { type SyntheticEvent } from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';

export type ApiTabValue =
  | 'overview'
  | 'versions'
  | 'specification'
  | 'deployments'
  | 'metadata-quality'
  | 'inspector';

export interface ApiTabsProps {
  value: ApiTabValue;
  onChange: (tab: ApiTabValue) => void;
  /** Whether to show the MCP Inspector tab. Pass `true` for MCP APIs. */
  showInspector?: boolean;
  /** Whether the Inspector tab is clickable. Pass `false` when no server URL is available. */
  inspectorEnabled?: boolean;
}

const BASE_TAB_OPTIONS: { value: ApiTabValue; label: string }[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'versions', label: 'Versions' },
  { value: 'specification', label: 'Specification' },
  { value: 'deployments', label: 'Deployments' },
  { value: 'metadata-quality', label: 'Metadata Quality' },
];

export default function ApiTabs({
  value,
  onChange,
  showInspector = false,
  inspectorEnabled = true,
}: ApiTabsProps) {
  const handleChange = (_event: SyntheticEvent, newValue: ApiTabValue) => {
    onChange(newValue);
  };

  const inspectorTab = showInspector ? (
    <Tooltip
      key="inspector"
      title={inspectorEnabled ? '' : 'No deployment URL available'}
      placement="top"
    >
      {/* Tooltip requires a single focusable child; wrap disabled Tab in span */}
      <span>
        <Tab
          label="Inspector"
          value="inspector"
          disabled={!inspectorEnabled}
          data-testid="inspector-tab"
        />
      </span>
    </Tooltip>
  ) : null;

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }} data-testid="api-tabs">
      <Tabs
        value={value}
        onChange={handleChange}
        aria-label="API detail sections"
        variant="scrollable"
        scrollButtons="auto"
      >
        {BASE_TAB_OPTIONS.map((tab) => (
          <Tab key={tab.value} label={tab.label} value={tab.value} />
        ))}
        {inspectorTab}
      </Tabs>
    </Box>
  );
}
