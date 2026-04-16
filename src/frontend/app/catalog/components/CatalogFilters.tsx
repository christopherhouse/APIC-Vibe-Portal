'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import FormControl from '@mui/material/FormControl';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import { ApiLifecycle, ApiKind } from '@apic-vibe-portal/shared';

/** Human-readable labels for lifecycle values. */
const LIFECYCLE_OPTIONS: { value: ApiLifecycle; label: string }[] = [
  { value: ApiLifecycle.Design, label: 'Design' },
  { value: ApiLifecycle.Development, label: 'Development' },
  { value: ApiLifecycle.Testing, label: 'Testing' },
  { value: ApiLifecycle.Preview, label: 'Preview' },
  { value: ApiLifecycle.Production, label: 'Production' },
  { value: ApiLifecycle.Deprecated, label: 'Deprecated' },
  { value: ApiLifecycle.Retired, label: 'Retired' },
];

/** Human-readable labels for kind values. */
const KIND_OPTIONS: { value: ApiKind; label: string }[] = [
  { value: ApiKind.REST, label: 'REST' },
  { value: ApiKind.GraphQL, label: 'GraphQL' },
  { value: ApiKind.GRPC, label: 'gRPC' },
  { value: ApiKind.SOAP, label: 'SOAP' },
];

export interface CatalogFiltersProps {
  selectedLifecycle?: string;
  selectedKind?: string;
  onLifecycleChange: (lifecycle: string | undefined) => void;
  onKindChange: (kind: string | undefined) => void;
}

export default function CatalogFilters({
  selectedLifecycle,
  selectedKind,
  onLifecycleChange,
  onKindChange,
}: CatalogFiltersProps) {
  const hasFilters = selectedLifecycle !== undefined || selectedKind !== undefined;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2" gutterBottom sx={{ mb: 0 }}>
          Filters
        </Typography>
        {hasFilters && (
          <Button
            size="small"
            onClick={() => {
              onLifecycleChange(undefined);
              onKindChange(undefined);
            }}
          >
            Clear all
          </Button>
        )}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        Lifecycle Stage
      </Typography>
      <FormControl>
        <RadioGroup
          value={selectedLifecycle ?? ''}
          onChange={(e) => onLifecycleChange(e.target.value || undefined)}
        >
          {LIFECYCLE_OPTIONS.map((opt) => (
            <FormControlLabel
              key={opt.value}
              value={opt.value}
              control={<Radio size="small" />}
              label={<Typography variant="body2">{opt.label}</Typography>}
              aria-label={`Filter by ${opt.label}`}
            />
          ))}
        </RadioGroup>
      </FormControl>

      <Divider sx={{ my: 1.5 }} />

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        API Kind
      </Typography>
      <FormControl>
        <RadioGroup
          value={selectedKind ?? ''}
          onChange={(e) => onKindChange(e.target.value || undefined)}
        >
          {KIND_OPTIONS.map((opt) => (
            <FormControlLabel
              key={opt.value}
              value={opt.value}
              control={<Radio size="small" />}
              label={<Typography variant="body2">{opt.label}</Typography>}
              aria-label={`Filter by ${opt.label}`}
            />
          ))}
        </RadioGroup>
      </FormControl>
    </Box>
  );
}
