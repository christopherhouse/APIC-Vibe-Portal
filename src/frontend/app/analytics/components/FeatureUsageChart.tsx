'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { UserActivity } from '@/lib/analytics-api';

interface FeatureUsageChartProps {
  activity: UserActivity;
}

export default function FeatureUsageChart({ activity }: FeatureUsageChartProps) {
  const theme = useTheme();

  const { featureAdoption } = activity;

  const total =
    featureAdoption.catalog +
    featureAdoption.search +
    featureAdoption.chat +
    featureAdoption.compare +
    featureAdoption.governance;

  if (total === 0) {
    return (
      <Card data-testid="feature-usage-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Feature Adoption
          </Typography>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No feature usage data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const chartData = [
    { feature: 'Catalog', usage: featureAdoption.catalog },
    { feature: 'Search', usage: featureAdoption.search },
    { feature: 'Chat', usage: featureAdoption.chat },
    { feature: 'Compare', usage: featureAdoption.compare },
    { feature: 'Governance', usage: featureAdoption.governance },
  ];

  return (
    <Card data-testid="feature-usage-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Feature Adoption
        </Typography>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={chartData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="feature" tick={{ fontSize: 12 }} />
            <Radar
              name="Usage"
              dataKey="usage"
              stroke={theme.palette.primary.main}
              fill={theme.palette.primary.main}
              fillOpacity={0.3}
            />
            <Tooltip contentStyle={{ fontSize: 12 }} />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
