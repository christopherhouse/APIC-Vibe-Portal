'use client';

import { Box, Card, CardContent, Grid, Typography, LinearProgress } from '@mui/material';
import type { CompletenessOverviewData } from '@/lib/metadata-api';

interface CompletenessOverviewProps {
  overview: CompletenessOverviewData;
}

const GRADE_COLORS: Record<string, string> = {
  A: '#2e7d32',
  B: '#1b5e20',
  C: '#f57f17',
  D: '#e65100',
  F: '#c62828',
};

export default function CompletenessOverview({ overview }: CompletenessOverviewProps) {
  const gradeColor = GRADE_COLORS[overview.averageGrade] || GRADE_COLORS.F;

  return (
    <Card data-testid="completeness-overview-card">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Metadata Completeness
        </Typography>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography
                variant="h3"
                component="div"
                sx={{ color: gradeColor, fontWeight: 'bold' }}
              >
                {overview.averageGrade}
              </Typography>
              <Typography variant="h5" component="div">
                {overview.averageScore.toFixed(1)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Average Score ({overview.totalApis} APIs)
              </Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Typography variant="subtitle2" gutterBottom>
              Grade Distribution
            </Typography>
            {Object.entries(overview.distribution).map(([grade, count]) => (
              <Box key={grade} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Typography
                  variant="body2"
                  sx={{ minWidth: 16, fontWeight: 'bold', color: GRADE_COLORS[grade] }}
                >
                  {grade}
                </Typography>
                <Box sx={{ flexGrow: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={overview.totalApis > 0 ? (count / overview.totalApis) * 100 : 0}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ minWidth: 20 }}>
                  {count}
                </Typography>
              </Box>
            ))}
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Typography variant="subtitle2" gutterBottom>
              Dimension Averages
            </Typography>
            {overview.dimensionAverages.map((dim) => (
              <Box key={dim.key} sx={{ mb: 0.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption">{dim.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {dim.averageScore.toFixed(0)}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={dim.averageScore}
                  sx={{ height: 4, borderRadius: 2 }}
                />
              </Box>
            ))}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}
