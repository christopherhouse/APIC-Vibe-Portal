'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
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
  selectedLifecycles: string[];
  selectedKinds: string[];
  onLifecycleChange: (lifecycles: string[]) => void;
  onKindChange: (kinds: string[]) => void;
}

export default function CatalogFilters({
  selectedLifecycles,
  selectedKinds,
  onLifecycleChange,
  onKindChange,
}: CatalogFiltersProps) {
  const handleLifecycleToggle = (value: string) => {
    const next = selectedLifecycles.includes(value)
      ? selectedLifecycles.filter((v) => v !== value)
      : [...selectedLifecycles, value];
    onLifecycleChange(next);
  };

  const handleKindToggle = (value: string) => {
    const next = selectedKinds.includes(value)
      ? selectedKinds.filter((v) => v !== value)
      : [...selectedKinds, value];
    onKindChange(next);
  };

  const hasFilters = selectedLifecycles.length > 0 || selectedKinds.length > 0;

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
              onLifecycleChange([]);
              onKindChange([]);
            }}
          >
            Clear all
          </Button>
        )}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        Lifecycle Stage
      </Typography>
      <FormGroup>
        {LIFECYCLE_OPTIONS.map((opt) => (
          <FormControlLabel
            key={opt.value}
            control={
              <Checkbox
                size="small"
                checked={selectedLifecycles.includes(opt.value)}
                onChange={() => handleLifecycleToggle(opt.value)}
                aria-label={`Filter by ${opt.label}`}
              />
            }
            label={<Typography variant="body2">{opt.label}</Typography>}
          />
        ))}
      </FormGroup>

      <Divider sx={{ my: 1.5 }} />

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        API Kind
      </Typography>
      <FormGroup>
        {KIND_OPTIONS.map((opt) => (
          <FormControlLabel
            key={opt.value}
            control={
              <Checkbox
                size="small"
                checked={selectedKinds.includes(opt.value)}
                onChange={() => handleKindToggle(opt.value)}
                aria-label={`Filter by ${opt.label}`}
              />
            }
            label={<Typography variant="body2">{opt.label}</Typography>}
          />
        ))}
      </FormGroup>
    </Box>
  );
}
