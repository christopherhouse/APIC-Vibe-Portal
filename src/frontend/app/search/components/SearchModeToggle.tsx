'use client';

import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import type { SearchMode } from '@/lib/search-api';

const MODES: { value: SearchMode; label: string; tooltip: string }[] = [
  {
    value: 'keyword',
    label: 'Keyword',
    tooltip: 'Traditional full-text search using exact keyword matching.',
  },
  {
    value: 'semantic',
    label: 'Semantic',
    tooltip: 'AI-powered search that understands the meaning of your query.',
  },
  {
    value: 'hybrid',
    label: 'Hybrid',
    tooltip: 'Best of both: combines keyword and semantic search for optimal results.',
  },
];

export interface SearchModeToggleProps {
  mode: SearchMode;
  onChange: (mode: SearchMode) => void;
}

export default function SearchModeToggle({ mode, onChange }: SearchModeToggleProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }} data-testid="search-mode-toggle">
      <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
        Search mode:
      </Typography>
      <ToggleButtonGroup
        value={mode}
        exclusive
        size="small"
        onChange={(_, newMode: SearchMode | null) => {
          if (newMode) onChange(newMode);
        }}
        aria-label="search mode"
      >
        {MODES.map(({ value, label, tooltip }) => (
          <Tooltip key={value} title={tooltip} placement="bottom" arrow>
            <ToggleButton value={value} aria-label={`${label} search mode`}>
              {label}
            </ToggleButton>
          </Tooltip>
        ))}
      </ToggleButtonGroup>
    </Box>
  );
}
