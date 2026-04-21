'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { PopularApi } from '@/lib/analytics-api';

interface PopularApisChartProps {
  apis: PopularApi[];
}

export default function PopularApisChart({ apis }: PopularApisChartProps) {
  const theme = useTheme();

  if (apis.length === 0) {
    return (
      <Card data-testid="popular-apis-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Top APIs by Views
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

  const chartData = apis.slice(0, 10).map((api) => ({
    name: api.apiName.length > 22 ? `${api.apiName.substring(0, 22)}…` : api.apiName,
    views: api.viewCount,
    downloads: api.downloadCount,
  }));

  return (
    <Card data-testid="popular-apis-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Top APIs by Views
        </Typography>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 160, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 12 }} />
            <YAxis dataKey="name" type="category" width={155} tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Bar dataKey="views" name="Views" fill={theme.palette.primary.main} />
            <Bar dataKey="downloads" name="Downloads" fill={theme.palette.secondary.main} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
