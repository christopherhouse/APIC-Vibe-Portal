'use client';

import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import LinearProgress from '@mui/material/LinearProgress';
import Tooltip from '@mui/material/Tooltip';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { useRouter } from 'next/navigation';
import { ApiLifecycle, ApiKind } from '@apic-vibe-portal/shared';
import type { SearchResultItem } from '@/lib/search-api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const LIFECYCLE_COLOR_MAP: Record<
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

const KIND_LABEL_MAP: Record<string, string> = {
  [ApiKind.REST]: 'REST',
  [ApiKind.GraphQL]: 'GraphQL',
  [ApiKind.GRPC]: 'gRPC',
  [ApiKind.SOAP]: 'SOAP',
  [ApiKind.WebSocket]: 'WebSocket',
  [ApiKind.Webhook]: 'Webhook',
};

/**
 * Render a string that may contain `<em>` highlight tags.
 * We use dangerouslySetInnerHTML only on text returned by the controlled BFF.
 */
function HighlightedText({ html, className }: { html: string; className?: string }) {
  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
      data-testid="highlighted-text"
    />
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface SearchResultCardProps {
  result: SearchResultItem;
}

export default function SearchResultCard({ result }: SearchResultCardProps) {
  const router = useRouter();

  const lifecycleLabel =
    result.lifecycleStage.charAt(0).toUpperCase() + result.lifecycleStage.slice(1);
  const lifecycleColor = LIFECYCLE_COLOR_MAP[result.lifecycleStage] ?? 'default';
  const kindLabel = KIND_LABEL_MAP[result.kind] ?? result.kind.toUpperCase();

  // Prefer highlighted title/description when available
  const titleHtml = result.highlights?.title?.[0] ?? result.title;
  const descriptionHtml = result.highlights?.description?.[0] ?? result.description;

  const relevancePct = Math.round(Math.min(result.score ?? 0, 1) * 100);

  return (
    <Card
      data-testid={`search-result-${result.apiId}`}
      variant="outlined"
      sx={{
        mb: 2,
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 4 },
        '& em': {
          fontStyle: 'normal',
          backgroundColor: 'warning.light',
          borderRadius: '2px',
          px: 0.25,
        },
      }}
    >
      <CardActionArea onClick={() => router.push(`/catalog/${result.apiId}`)}>
        <CardContent>
          {/* Header row */}
          <Stack direction="row" spacing={1} sx={{ mb: 1, alignItems: 'center' }}>
            <Chip label={kindLabel} size="small" variant="outlined" />
            <Chip label={lifecycleLabel} size="small" color={lifecycleColor} />
            <Box sx={{ flex: 1 }} />
            {result.score !== undefined && (
              <Tooltip title={`Relevance: ${relevancePct}%`} placement="left">
                <Box sx={{ width: 64, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <LinearProgress
                    variant="determinate"
                    value={relevancePct}
                    sx={{ flex: 1, height: 4, borderRadius: 2 }}
                    aria-label={`Relevance score ${relevancePct}%`}
                  />
                </Box>
              </Tooltip>
            )}
          </Stack>

          {/* Title */}
          <Typography variant="h6" component="h2" gutterBottom sx={{ lineHeight: 1.3 }}>
            <HighlightedText html={titleHtml} />
          </Typography>

          {/* Semantic caption (AI summary) */}
          {result.semanticCaption && (
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5, mb: 1 }}>
              <AutoAwesomeIcon sx={{ fontSize: 14, color: 'secondary.main', mt: 0.3 }} />
              <Typography
                variant="body2"
                color="secondary.main"
                sx={{ fontStyle: 'italic' }}
                data-testid="semantic-caption"
              >
                {result.semanticCaption}
              </Typography>
            </Box>
          )}

          {/* Description */}
          <Typography variant="body2" color="text.secondary">
            <HighlightedText html={descriptionHtml} />
          </Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}
