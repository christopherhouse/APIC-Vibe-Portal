'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Alert,
  Box,
  CircularProgress,
  Container,
  Grid,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import Link from 'next/link';
import BlockIcon from '@mui/icons-material/Block';
import { useAuth } from '@/lib/auth/use-auth';
import { fetchUserActivity, type TimeRange, type UserActivity } from '@/lib/analytics-api';
import TimeRangeSelector from '../components/TimeRangeSelector';
import UserEngagementChart from '../components/UserEngagementChart';
import FeatureUsageChart from '../components/FeatureUsageChart';
import ExportButton from '../components/ExportButton';

const ALLOWED_ROLES = ['Portal.Admin', 'Portal.Maintainer'];

export default function UserEngagementPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const hasAccess = Boolean(user?.roles.some((r) => ALLOWED_ROLES.includes(r)));

  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [activity, setActivity] = useState<UserActivity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchUserActivity(timeRange);
      setActivity(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load user engagement data');
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    if (isAuthenticated && hasAccess) {
      void loadData();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [isAuthenticated, hasAccess, authLoading, loadData]);

  if (authLoading) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (!hasAccess && !authLoading) {
    return (
      <Container maxWidth="sm" sx={{ py: 8, textAlign: 'center' }}>
        <BlockIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Access Denied
        </Typography>
        <Typography variant="body1" color="text.secondary">
          You need the <strong>Portal.Admin</strong> or <strong>Portal.Maintainer</strong> role to
          view analytics.
        </Typography>
      </Container>
    );
  }

  if (loading && !activity) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress data-testid="user-engagement-loading" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error" data-testid="user-engagement-error">
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }} data-testid="user-engagement-dashboard">
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          mb: 3,
          flexWrap: 'wrap',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h4" component="h1">
            User Engagement
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Active users, session metrics, and feature adoption
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          {activity && activity.dailyActiveUsers.length > 0 && (
            <ExportButton
              getData={() =>
                activity.dailyActiveUsers.map((d) => ({
                  date: d.date,
                  activeUsers: d.count,
                }))
              }
              filename={`user-engagement-${timeRange}.csv`}
            />
          )}
        </Box>
      </Box>

      {/* Sub-navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={3} aria-label="analytics sections">
          <Tab label="Overview" component={Link} href="/analytics" />
          <Tab label="Search" component={Link} href="/analytics/search" />
          <Tab label="APIs" component={Link} href="/analytics/apis" />
          <Tab label="Users" component={Link} href="/analytics/users" />
        </Tabs>
      </Box>

      {activity && (
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <UserEngagementChart activity={activity} />
          </Grid>
          <Grid size={{ xs: 12, lg: 4 }}>
            <FeatureUsageChart activity={activity} />
          </Grid>
        </Grid>
      )}
    </Container>
  );
}
