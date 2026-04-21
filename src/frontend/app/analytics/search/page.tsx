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
import { fetchSearchTrends, type TimeRange, type SearchTrends } from '@/lib/analytics-api';
import TimeRangeSelector from '../components/TimeRangeSelector';
import SearchQueryList from '../components/SearchQueryList';
import SearchEffectivenessChart from '../components/SearchEffectivenessChart';
import ExportButton from '../components/ExportButton';

const ALLOWED_ROLES = ['Portal.Admin', 'Portal.Maintainer'];

export default function SearchAnalyticsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const hasAccess = Boolean(user?.roles.some((r) => ALLOWED_ROLES.includes(r)));

  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [searchTrends, setSearchTrends] = useState<SearchTrends | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSearchTrends(timeRange);
      setSearchTrends(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load search analytics');
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

  if (loading && !searchTrends) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress data-testid="search-analytics-loading" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4 }}>
        <Alert severity="error" data-testid="search-analytics-error">
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }} data-testid="search-analytics-dashboard">
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
            Search Analytics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Search query volume, effectiveness, and top terms
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          {searchTrends && searchTrends.topQueries.length > 0 && (
            <ExportButton
              getData={() =>
                searchTrends.topQueries.map((q) => ({
                  term: q.displayTerm,
                  count: q.count,
                  avgResults: q.avgResultCount,
                }))
              }
              filename={`search-analytics-${timeRange}.csv`}
            />
          )}
        </Box>
      </Box>

      {/* Sub-navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={1} aria-label="analytics sections">
          <Tab label="Overview" component={Link} href="/analytics" />
          <Tab label="Search" component={Link} href="/analytics/search" />
          <Tab label="APIs" component={Link} href="/analytics/apis" />
          <Tab label="Users" component={Link} href="/analytics/users" />
        </Tabs>
      </Box>

      {searchTrends && (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12 }}>
              <SearchEffectivenessChart trends={searchTrends} />
            </Grid>
          </Grid>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <SearchQueryList trends={searchTrends} />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Zero Result Queries
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  These searches returned no results — opportunities for improvement
                </Typography>
                {searchTrends.zeroResultQueries.length === 0 ? (
                  <Typography variant="body2" color="success.main">
                    No zero-result queries in this period 🎉
                  </Typography>
                ) : (
                  searchTrends.zeroResultQueries.slice(0, 10).map((q, i) => (
                    <Box
                      key={i}
                      sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}
                      data-testid={`zero-result-query-${i}`}
                    >
                      <Typography variant="body2">{q.displayTerm}</Typography>
                      <Typography variant="body2" color="error.main">
                        {q.count} times
                      </Typography>
                    </Box>
                  ))
                )}
              </Box>
            </Grid>
          </Grid>
        </>
      )}
    </Container>
  );
}
