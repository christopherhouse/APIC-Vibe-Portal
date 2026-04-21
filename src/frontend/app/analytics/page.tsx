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
import {
  fetchAnalyticsSummary,
  fetchUsageTrends,
  fetchPopularApis,
  fetchSearchTrends,
  type TimeRange,
  type AnalyticsSummary,
  type UsageTrends,
  type PopularApi,
  type SearchTrends,
} from '@/lib/analytics-api';
import AnalyticsOverview from './components/AnalyticsOverview';
import TimeRangeSelector from './components/TimeRangeSelector';
import UsageTrendChart from './components/UsageTrendChart';
import PopularApisChart from './components/PopularApisChart';
import SearchQueryList from './components/SearchQueryList';
import ExportButton from './components/ExportButton';

const ALLOWED_ROLES = ['Portal.Admin', 'Portal.Maintainer'];

export default function AnalyticsDashboardPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const hasAccess = Boolean(user?.roles.some((r) => ALLOWED_ROLES.includes(r)));

  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<UsageTrends | null>(null);
  const [popularApis, setPopularApis] = useState<PopularApi[]>([]);
  const [searchTrends, setSearchTrends] = useState<SearchTrends | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, trendsData, apisData, searchData] = await Promise.all([
        fetchAnalyticsSummary(timeRange),
        fetchUsageTrends(timeRange),
        fetchPopularApis(timeRange),
        fetchSearchTrends(timeRange),
      ]);
      setSummary(summaryData);
      setTrends(trendsData);
      setPopularApis(apisData);
      setSearchTrends(searchData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data');
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
        <BlockIcon
          sx={{ fontSize: 64, color: 'error.main', mb: 2 }}
          data-testid="access-denied-icon"
        />
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

  if (loading && !summary) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress data-testid="analytics-loading" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error" data-testid="analytics-error">
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }} data-testid="analytics-dashboard">
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
            Analytics Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Portal usage, API popularity, and user engagement insights
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          {popularApis.length > 0 && (
            <ExportButton
              getData={() =>
                popularApis.map((api) => ({
                  apiId: api.apiId,
                  apiName: api.apiName,
                  views: api.viewCount,
                  downloads: api.downloadCount,
                  chatMentions: api.chatMentionCount,
                }))
              }
              filename={`analytics-apis-${timeRange}.csv`}
            />
          )}
        </Box>
      </Box>

      {/* Sub-navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={0} aria-label="analytics sections">
          <Tab label="Overview" component={Link} href="/analytics" />
          <Tab label="Search" component={Link} href="/analytics/search" />
          <Tab label="APIs" component={Link} href="/analytics/apis" />
          <Tab label="Users" component={Link} href="/analytics/users" />
        </Tabs>
      </Box>

      {/* KPI Cards */}
      {summary && (
        <Box sx={{ mb: 4 }}>
          <AnalyticsOverview summary={summary} />
        </Box>
      )}

      {/* Charts */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, lg: 8 }}>{trends && <UsageTrendChart trends={trends} />}</Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          {searchTrends && <SearchQueryList trends={searchTrends} />}
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12 }}>
          <PopularApisChart apis={popularApis} />
        </Grid>
      </Grid>
    </Container>
  );
}
