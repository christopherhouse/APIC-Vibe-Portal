'use client';

import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import ViewListIcon from '@mui/icons-material/ViewList';

export type ViewMode = 'grid' | 'list';

export interface ViewToggleProps {
  viewMode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

export default function ViewToggle({ viewMode, onChange }: ViewToggleProps) {
  const handleChange = (_event: React.MouseEvent<HTMLElement>, value: ViewMode | null) => {
    if (value !== null) {
      onChange(value);
    }
  };

  return (
    <ToggleButtonGroup
      value={viewMode}
      exclusive
      onChange={handleChange}
      aria-label="View mode"
      size="small"
    >
      <ToggleButton value="grid" aria-label="Grid view">
        <ViewModuleIcon />
      </ToggleButton>
      <ToggleButton value="list" aria-label="List view">
        <ViewListIcon />
      </ToggleButton>
    </ToggleButtonGroup>
  );
}
