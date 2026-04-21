'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { ScoreDistribution } from '@/lib/governance-api';

interface ScoreDistributionChartProps {
  distribution: ScoreDistribution;
}

export default function ScoreDistributionChart({ distribution }: ScoreDistributionChartProps) {
  const theme = useTheme();

  const data = [
    { name: 'Excellent', value: distribution.excellent, color: theme.palette.success.main },
    { name: 'Good', value: distribution.good, color: theme.palette.primary.main },
    {
      name: 'Needs Improvement',
      value: distribution.needsImprovement,
      color: theme.palette.warning.main,
    },
    { name: 'Poor', value: distribution.poor, color: theme.palette.error.main },
  ];

  const total = data.reduce((sum, item) => sum + item.value, 0);

  if (total === 0) {
    return (
      <Card data-testid="score-distribution-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Score Distribution
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

  return (
    <Card data-testid="score-distribution-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Score Distribution
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
