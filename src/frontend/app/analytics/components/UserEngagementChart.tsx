'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { UserActivity } from '@/lib/analytics-api';

interface UserEngagementChartProps {
  activity: UserActivity;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function UserEngagementChart({ activity }: UserEngagementChartProps) {
  const theme = useTheme();

  if (activity.dailyActiveUsers.length === 0) {
    return (
      <Card data-testid="user-engagement-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Daily Active Users
          </Typography>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No user data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const chartData = activity.dailyActiveUsers.map((point) => ({
    date: formatDate(point.date),
    users: point.count,
  }));

  return (
    <Card data-testid="user-engagement-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Daily Active Users
        </Typography>
        <Box sx={{ display: 'flex', gap: 3, mb: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Avg Session
            </Typography>
            <Typography variant="h6" color="primary">
              {Math.round(activity.avgSessionDurationSeconds / 60)}m
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Pages / Session
            </Typography>
            <Typography variant="h6" color="primary">
              {activity.avgPagesPerSession.toFixed(1)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Return Rate
            </Typography>
            <Typography variant="h6" color="primary">
              {activity.returningUserRate.toFixed(1)}%
            </Typography>
          </Box>
        </Box>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Area
              type="monotone"
              dataKey="users"
              name="Active Users"
              stroke={theme.palette.primary.main}
              fill={theme.palette.primary.light}
              fillOpacity={0.3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
