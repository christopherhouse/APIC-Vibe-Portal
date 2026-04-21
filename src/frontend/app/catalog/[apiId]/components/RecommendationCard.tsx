'use client';

import { Box, Card, CardContent, Chip, Typography } from '@mui/material';
import type { Recommendation } from '@/lib/metadata-api';

interface RecommendationCardProps {
  recommendation: Recommendation;
}

const IMPACT_LABELS: Record<number, string> = {
  3: 'High Impact',
  2: 'Medium Impact',
  1: 'Low Impact',
};

const IMPACT_COLORS: Record<number, 'error' | 'warning' | 'info'> = {
  3: 'error',
  2: 'warning',
  1: 'info',
};

const EFFORT_COLORS: Record<string, 'success' | 'warning' | 'error'> = {
  low: 'success',
  medium: 'warning',
  high: 'error',
};

export default function RecommendationCard({ recommendation }: RecommendationCardProps) {
  return (
    <Card
      variant="outlined"
      data-testid={`recommendation-card-${recommendation.id}`}
      sx={{ mb: 2 }}
    >
      <CardContent>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            mb: 1,
          }}
        >
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
            #{recommendation.priority} — {recommendation.title}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip
              label={IMPACT_LABELS[recommendation.impact] || 'Unknown'}
              color={IMPACT_COLORS[recommendation.impact] || 'default'}
              size="small"
              data-testid="impact-chip"
            />
            <Chip
              label={`${recommendation.effort} effort`}
              color={EFFORT_COLORS[recommendation.effort] || 'default'}
              size="small"
              variant="outlined"
              data-testid="effort-chip"
            />
          </Box>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {recommendation.description}
        </Typography>
        <Box sx={{ bgcolor: 'action.hover', p: 1.5, borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Example:
          </Typography>
          <Typography variant="body2">{recommendation.example}</Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
