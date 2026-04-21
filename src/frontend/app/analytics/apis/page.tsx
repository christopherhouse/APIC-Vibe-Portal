'use client';

import { useEffect, useState, useCallback } from 'react';
import { Alert, Box, CircularProgress, Container, Tab, Tabs, Typography } from '@mui/material';
import Link from 'next/link';
import BlockIcon from '@mui/icons-material/Block';
import { useAuth } from '@/lib/auth/use-auth';
import { fetchPopularApis, type TimeRange, type PopularApi } from '@/lib/analytics-api';
import TimeRangeSelector from '../components/TimeRangeSelector';
import PopularApisChart from '../components/PopularApisChart';
import ApiTrafficTable from '../components/ApiTrafficTable';
import ExportButton from '../components/ExportButton';

const ALLOWED_ROLES = ['Portal.Admin', 'Portal.Maintainer'];

export default function ApiPopularityPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const hasAccess = Boolean(user?.roles.some((r) => ALLOWED_ROLES.includes(r)));

  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [apis, setApis] = useState<PopularApi[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPopularApis(timeRange, 20);
      setApis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load API popularity data');
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

  if (loading && apis.length === 0) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress data-testid="api-popularity-loading" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error" data-testid="api-popularity-error">
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }} data-testid="api-popularity-dashboard">
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
            API Popularity
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Most viewed, downloaded, and discussed APIs
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          {apis.length > 0 && (
            <ExportButton
              getData={() =>
                apis.map((api) => ({
                  apiId: api.apiId,
                  apiName: api.apiName,
                  views: api.viewCount,
                  downloads: api.downloadCount,
                  chatMentions: api.chatMentionCount,
                }))
              }
              filename={`api-popularity-${timeRange}.csv`}
            />
          )}
        </Box>
      </Box>

      {/* Sub-navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={2} aria-label="analytics sections">
          <Tab label="Overview" component={Link} href="/analytics" />
          <Tab label="Search" component={Link} href="/analytics/search" />
          <Tab label="APIs" component={Link} href="/analytics/apis" />
          <Tab label="Users" component={Link} href="/analytics/users" />
        </Tabs>
      </Box>

      <Box sx={{ mb: 4 }}>
        <PopularApisChart apis={apis} />
      </Box>

      <Box>
        <Typography variant="h5" gutterBottom>
          API Traffic Details
        </Typography>
        <ApiTrafficTable apis={apis} />
      </Box>
    </Container>
  );
}
