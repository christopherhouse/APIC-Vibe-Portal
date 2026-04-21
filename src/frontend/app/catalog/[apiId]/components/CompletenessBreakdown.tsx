'use client';

import { Box, Card, CardContent, Typography, LinearProgress, Grid } from '@mui/material';
import type { DimensionScore } from '@/lib/metadata-api';

interface CompletenessBreakdownProps {
  dimensions: DimensionScore[];
}

function getProgressColor(score: number): 'success' | 'warning' | 'error' {
  if (score >= 75) return 'success';
  if (score >= 50) return 'warning';
  return 'error';
}

export default function CompletenessBreakdown({ dimensions }: CompletenessBreakdownProps) {
  return (
    <Card data-testid="completeness-breakdown-card">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Dimension Breakdown
        </Typography>
        <Grid container spacing={2}>
          {dimensions.map((dim) => (
            <Grid size={{ xs: 12 }} key={dim.key} data-testid={`dimension-${dim.key}`}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2">{dim.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {dim.score.toFixed(0)}/100 ({(dim.weight * 100).toFixed(0)}% weight)
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={dim.score}
                color={getProgressColor(dim.score)}
                sx={{ height: 8, borderRadius: 4 }}
                data-testid={`dimension-progress-${dim.key}`}
              />
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}
