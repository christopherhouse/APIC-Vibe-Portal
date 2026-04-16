'use client';

import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import type { SelectChangeEvent } from '@mui/material/Select';
import Skeleton from '@mui/material/Skeleton';
import type { ApiVersion } from '@apic-vibe-portal/shared';
import { ApiLifecycle } from '@apic-vibe-portal/shared';
import { formatDate } from '@/lib/utils';

/** Color mapping for lifecycle stages. */
const lifecycleColorMap: Record<
  string,
  'success' | 'info' | 'warning' | 'error' | 'default' | 'primary' | 'secondary'
> = {
  [ApiLifecycle.Production]: 'success',
  [ApiLifecycle.Development]: 'info',
  [ApiLifecycle.Design]: 'default',
  [ApiLifecycle.Testing]: 'info',
  [ApiLifecycle.Preview]: 'secondary',
  [ApiLifecycle.Deprecated]: 'warning',
  [ApiLifecycle.Retired]: 'error',
};

export interface ApiVersionListProps {
  versions: ApiVersion[];
  selectedVersionId: string | null;
  onVersionChange: (versionId: string) => void;
  isLoading?: boolean;
}

export default function ApiVersionList({
  versions,
  selectedVersionId,
  onVersionChange,
  isLoading,
}: ApiVersionListProps) {
  if (isLoading) {
    return (
      <Box data-testid="version-list-skeleton">
        <Skeleton variant="rounded" width={200} height={56} sx={{ mb: 2 }} />
        <Skeleton variant="rounded" height={200} />
      </Box>
    );
  }

  if (versions.length === 0) {
    return (
      <Box data-testid="version-list-empty">
        <Typography variant="body1" color="text.secondary">
          No versions available for this API.
        </Typography>
      </Box>
    );
  }

  const handleSelectChange = (event: SelectChangeEvent) => {
    onVersionChange(event.target.value);
  };

  return (
    <Box data-testid="version-list">
      {/* Version Selector */}
      <FormControl sx={{ mb: 3, minWidth: 200 }} size="small">
        <InputLabel id="version-selector-label">Select Version</InputLabel>
        <Select
          labelId="version-selector-label"
          label="Select Version"
          value={selectedVersionId ?? ''}
          onChange={handleSelectChange}
          data-testid="version-selector"
        >
          {versions.map((version) => (
            <MenuItem key={version.id} value={version.id}>
              {version.title}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Version Table */}
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Version</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Lifecycle</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Created</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Updated</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {versions.map((version) => {
              const lifecycleLabel =
                version.lifecycleStage.charAt(0).toUpperCase() +
                version.lifecycleStage.slice(1);
              const lifecycleColor =
                lifecycleColorMap[version.lifecycleStage] ?? 'default';
              const isSelected = version.id === selectedVersionId;

              return (
                <TableRow
                  key={version.id}
                  selected={isSelected}
                  data-testid={`version-row-${version.id}`}
                  sx={{ cursor: 'pointer' }}
                  tabIndex={0}
                  role="button"
                  onClick={() => onVersionChange(version.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      onVersionChange(version.id);
                    }
                  }}
                >
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: isSelected ? 700 : 400 }}
                    >
                      {version.title}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={lifecycleLabel}
                      size="small"
                      color={lifecycleColor}
                    />
                  </TableCell>
                  <TableCell>{formatDate(version.createdAt)}</TableCell>
                  <TableCell>{formatDate(version.updatedAt)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
