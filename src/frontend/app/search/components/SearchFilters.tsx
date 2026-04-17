'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import FormControl from '@mui/material/FormControl';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import { ApiLifecycle, ApiKind } from '@apic-vibe-portal/shared';
import type { SearchFacets } from '@/lib/search-api';

// ---------------------------------------------------------------------------
// Static filter options (always shown)
// ---------------------------------------------------------------------------

const LIFECYCLE_OPTIONS: { value: ApiLifecycle; label: string }[] = [
  { value: ApiLifecycle.Design, label: 'Design' },
  { value: ApiLifecycle.Development, label: 'Development' },
  { value: ApiLifecycle.Testing, label: 'Testing' },
  { value: ApiLifecycle.Preview, label: 'Preview' },
  { value: ApiLifecycle.Production, label: 'Production' },
  { value: ApiLifecycle.Deprecated, label: 'Deprecated' },
  { value: ApiLifecycle.Retired, label: 'Retired' },
];

const KIND_OPTIONS: { value: ApiKind; label: string }[] = [
  { value: ApiKind.REST, label: 'REST' },
  { value: ApiKind.GraphQL, label: 'GraphQL' },
  { value: ApiKind.GRPC, label: 'gRPC' },
  { value: ApiKind.SOAP, label: 'SOAP' },
  { value: ApiKind.WebSocket, label: 'WebSocket' },
  { value: ApiKind.Webhook, label: 'Webhook' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface SearchFiltersProps {
  selectedLifecycle?: string;
  selectedKind?: string;
  facets?: SearchFacets;
  onLifecycleChange: (value: string | undefined) => void;
  onKindChange: (value: string | undefined) => void;
}

/**
 * Count helper — looks up a facet count from the search response.
 * Returns undefined when facets are not yet loaded.
 */
function getFacetCount(
  facets: SearchFacets | undefined,
  field: 'kind' | 'lifecycle',
  value: string
): number | undefined {
  if (!facets) return undefined;
  const list = facets[field];
  return list.find((f) => f.value === value)?.count;
}

export default function SearchFilters({
  selectedLifecycle,
  selectedKind,
  facets,
  onLifecycleChange,
  onKindChange,
}: SearchFiltersProps) {
  const hasFilters = selectedLifecycle !== undefined || selectedKind !== undefined;

  return (
    <Box data-testid="search-filters">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2" sx={{ mb: 0 }}>
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

      {/* Lifecycle */}
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        Lifecycle Stage
      </Typography>
      <FormControl>
        <RadioGroup
          value={selectedLifecycle ?? ''}
          onChange={(e) => onLifecycleChange(e.target.value || undefined)}
        >
          {LIFECYCLE_OPTIONS.map((opt) => {
            const count = getFacetCount(facets, 'lifecycle', opt.value);
            return (
              <FormControlLabel
                key={opt.value}
                value={opt.value}
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2">{opt.label}</Typography>
                    {count !== undefined && (
                      <Chip
                        label={count}
                        size="small"
                        sx={{ height: 18, fontSize: '0.65rem' }}
                        data-testid={`facet-lifecycle-${opt.value}`}
                      />
                    )}
                  </Box>
                }
                aria-label={`Filter by ${opt.label}`}
              />
            );
          })}
        </RadioGroup>
      </FormControl>

      <Divider sx={{ my: 1.5 }} />

      {/* Kind */}
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        API Kind
      </Typography>
      <FormControl>
        <RadioGroup
          value={selectedKind ?? ''}
          onChange={(e) => onKindChange(e.target.value || undefined)}
        >
          {KIND_OPTIONS.map((opt) => {
            const count = getFacetCount(facets, 'kind', opt.value);
            return (
              <FormControlLabel
                key={opt.value}
                value={opt.value}
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2">{opt.label}</Typography>
                    {count !== undefined && (
                      <Chip
                        label={count}
                        size="small"
                        sx={{ height: 18, fontSize: '0.65rem' }}
                        data-testid={`facet-kind-${opt.value}`}
                      />
                    )}
                  </Box>
                }
                aria-label={`Filter by ${opt.label}`}
              />
            );
          })}
        </RadioGroup>
      </FormControl>
    </Box>
  );
}
