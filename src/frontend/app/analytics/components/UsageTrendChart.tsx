'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { UsageTrends } from '@/lib/analytics-api';

interface UsageTrendChartProps {
  trends: UsageTrends;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function UsageTrendChart({ trends }: UsageTrendChartProps) {
  const theme = useTheme();

  if (trends.dataPoints.length === 0) {
    return (
      <Card data-testid="usage-trend-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Usage Trends
          </Typography>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const chartData = trends.dataPoints.map((point) => ({
    ...point,
    date: formatDate(point.date),
  }));

  return (
    <Card data-testid="usage-trend-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Usage Trends
        </Typography>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Legend />
            <Line
              type="monotone"
              dataKey="activeUsers"
              name="Active Users"
              stroke={theme.palette.primary.main}
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="searches"
              name="Searches"
              stroke={theme.palette.secondary.main}
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="chatInteractions"
              name="Chat"
              stroke={theme.palette.success.main}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
