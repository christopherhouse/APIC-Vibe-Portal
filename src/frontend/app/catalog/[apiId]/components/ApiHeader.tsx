'use client';

import Breadcrumbs from '@mui/material/Breadcrumbs';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Link from '@mui/material/Link';
import Skeleton from '@mui/material/Skeleton';
import NextLink from 'next/link';
import type { ApiDefinition } from '@apic-vibe-portal/shared';
import { ApiLifecycle, ApiKind } from '@apic-vibe-portal/shared';
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

/** Human-readable labels for API kinds. */
const kindLabelMap: Record<string, string> = {
  [ApiKind.REST]: 'REST',
  [ApiKind.GraphQL]: 'GraphQL',
  [ApiKind.GRPC]: 'gRPC',
  [ApiKind.SOAP]: 'SOAP',
  [ApiKind.WebSocket]: 'WebSocket',
  [ApiKind.Webhook]: 'Webhook',
  [ApiKind.MCP]: 'MCP',
};

export interface ApiHeaderProps {
  api: ApiDefinition | null;
  isLoading?: boolean;
}

export default function ApiHeader({ api, isLoading }: ApiHeaderProps) {
  if (isLoading || !api) {
    return (
      <Box data-testid="api-header-skeleton">
        <Skeleton variant="text" width={200} height={24} sx={{ mb: 1 }} />
        <Skeleton variant="text" width={300} height={48} sx={{ mb: 1 }} />
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <Skeleton variant="rounded" width={60} height={24} />
          <Skeleton variant="rounded" width={80} height={24} />
        </Box>
        <Skeleton variant="text" width="60%" height={24} />
      </Box>
    );
  }

  const lifecycleLabel = api.lifecycleStage.charAt(0).toUpperCase() + api.lifecycleStage.slice(1);
  const lifecycleColor = lifecycleColorMap[api.lifecycleStage] ?? 'default';
  const kindLabel = kindLabelMap[api.kind] ?? api.kind.toUpperCase();

  return (
    <Box data-testid="api-header">
      {/* Breadcrumb */}
      <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 1 }}>
        <Link component={NextLink} href="/catalog" underline="hover" color="inherit">
          Catalog
        </Link>
        <Typography color="text.primary">{api.title}</Typography>
      </Breadcrumbs>

      {/* Title */}
      <Typography variant="h4" component="h1" gutterBottom>
        {api.title}
      </Typography>

      {/* Badges */}
      <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
        <Chip label={kindLabel} size="small" variant="outlined" data-testid="kind-badge" />
        <Chip
          label={lifecycleLabel}
          size="small"
          color={lifecycleColor}
          data-testid="lifecycle-badge"
        />
      </Stack>

      {/* Description */}
      {api.description && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 1 }}>
          {api.description}
        </Typography>
      )}

      {/* Last updated */}
      <Typography variant="caption" color="text.secondary">
        Last updated {formatDate(api.updatedAt)}
      </Typography>
    </Box>
  );
}
