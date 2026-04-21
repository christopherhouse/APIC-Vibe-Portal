'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { SearchTrends } from '@/lib/analytics-api';

interface SearchEffectivenessChartProps {
  trends: SearchTrends;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function SearchEffectivenessChart({ trends }: SearchEffectivenessChartProps) {
  const theme = useTheme();

  if (trends.dailyVolume.length === 0) {
    return (
      <Card data-testid="search-effectiveness-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Search Volume &amp; Zero Results
          </Typography>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No search data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const chartData = trends.dailyVolume.map((point) => ({
    date: formatDate(point.date),
    queries: point.queryCount,
    zeroResults: point.zeroResultCount,
  }));

  return (
    <Card data-testid="search-effectiveness-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Search Volume &amp; Zero Results
        </Typography>
        <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Click-through Rate
            </Typography>
            <Typography variant="h5" color="primary">
              {trends.clickThroughRate.toFixed(1)}%
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Avg Results / Search
            </Typography>
            <Typography variant="h5" color="primary">
              {trends.avgResultsPerSearch.toFixed(1)}
            </Typography>
          </Box>
        </Box>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Legend />
            <Bar dataKey="queries" name="Total Queries" fill={theme.palette.primary.main} />
            <Bar
              dataKey="zeroResults"
              name="Zero Results"
              fill={theme.palette.error.main}
              opacity={0.8}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
