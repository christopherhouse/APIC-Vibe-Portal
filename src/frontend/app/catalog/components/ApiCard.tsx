'use client';

import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import { useRouter } from 'next/navigation';
import type { ApiCatalogItem } from '@apic-vibe-portal/shared';
import { ApiLifecycle, ApiKind } from '@apic-vibe-portal/shared';
import { formatDate, truncate } from '@/lib/utils';
import CompareAddButton from '@/app/compare/components/CompareAddButton';

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
};

export interface ApiCardProps {
  api: ApiCatalogItem;
  /** When true, render a compact list-row instead of a card. */
  listMode?: boolean;
}

export default function ApiCard({ api, listMode = false }: ApiCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/catalog/${api.id}`);
  };

  const lifecycleLabel = api.lifecycleStage.charAt(0).toUpperCase() + api.lifecycleStage.slice(1);
  const lifecycleColor = lifecycleColorMap[api.lifecycleStage] ?? 'default';
  const kindLabel = kindLabelMap[api.kind] ?? api.kind.toUpperCase();

  if (listMode) {
    return (
      <Card variant="outlined" sx={{ mb: 1 }} data-testid={`api-card-${api.id}`}>
        <CardActionArea onClick={handleClick}>
          <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
              <Typography
                variant="subtitle1"
                component="span"
                sx={{ fontWeight: 600, minWidth: 200 }}
              >
                {api.title}
              </Typography>
              <Chip label={kindLabel} size="small" variant="outlined" />
              <Chip label={lifecycleLabel} size="small" color={lifecycleColor} />
              <Typography variant="body2" color="text.secondary" sx={{ flex: 1, minWidth: 150 }}>
                {truncate(api.description, 100)}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                Updated {formatDate(api.updatedAt)}
              </Typography>
              <CompareAddButton apiId={api.name} variant="icon" />
            </Box>
          </CardContent>
        </CardActionArea>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 4 },
      }}
      data-testid={`api-card-${api.id}`}
    >
      <CardActionArea
        onClick={handleClick}
        sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}
      >
        <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
            <Chip label={kindLabel} size="small" variant="outlined" />
            <Chip label={lifecycleLabel} size="small" color={lifecycleColor} />
          </Stack>
          <Typography variant="h6" component="h2" gutterBottom>
            {api.title}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ flex: 1, mb: 2 }}>
            {truncate(api.description, 150)}
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              {api.versionCount} version{api.versionCount !== 1 ? 's' : ''}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Updated {formatDate(api.updatedAt)}
              </Typography>
              <CompareAddButton apiId={api.name} variant="icon" />
            </Box>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}
