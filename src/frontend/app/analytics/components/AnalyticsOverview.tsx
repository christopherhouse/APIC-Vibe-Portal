'use client';

import { Box, Card, CardContent, Grid, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import PeopleIcon from '@mui/icons-material/People';
import PageviewIcon from '@mui/icons-material/Pageview';
import SearchIcon from '@mui/icons-material/Search';
import ChatIcon from '@mui/icons-material/Chat';
import TimerIcon from '@mui/icons-material/Timer';
import type { AnalyticsSummary } from '@/lib/analytics-api';

interface AnalyticsOverviewProps {
  summary: AnalyticsSummary;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${minutes}m ${secs}s`;
}

function TrendIcon({ value }: { value: number }) {
  if (value > 0) return <TrendingUpIcon color="success" fontSize="small" />;
  if (value < 0) return <TrendingDownIcon color="error" fontSize="small" />;
  return <TrendingFlatIcon color="disabled" fontSize="small" />;
}

function TrendText({ value }: { value: number }) {
  const sign = value > 0 ? '+' : '';
  const color = value > 0 ? 'success.main' : value < 0 ? 'error.main' : 'text.secondary';
  return (
    <Typography variant="body2" sx={{ color }}>
      {sign}
      {value.toFixed(1)}% vs previous period
    </Typography>
  );
}

export default function AnalyticsOverview({ summary }: AnalyticsOverviewProps) {
  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4 }}>
        <Card data-testid="total-users-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Total Users
              </Typography>
              <PeopleIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4" component="div">
              {summary.totalUsers.toLocaleString()}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
              <TrendIcon value={summary.usersTrend} />
              <TrendText value={summary.usersTrend} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4 }}>
        <Card data-testid="page-views-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Page Views
              </Typography>
              <PageviewIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4" component="div">
              {summary.totalPageViews.toLocaleString()}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
              <TrendIcon value={summary.pageViewsTrend} />
              <TrendText value={summary.pageViewsTrend} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4 }}>
        <Card data-testid="search-queries-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Search Queries
              </Typography>
              <SearchIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4" component="div">
              {summary.totalSearchQueries.toLocaleString()}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
              <TrendIcon value={summary.searchQueriesTrend} />
              <TrendText value={summary.searchQueriesTrend} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4 }}>
        <Card data-testid="chat-interactions-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Chat Interactions
              </Typography>
              <ChatIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4" component="div">
              {summary.totalChatInteractions.toLocaleString()}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
              <TrendIcon value={summary.chatInteractionsTrend} />
              <TrendText value={summary.chatInteractionsTrend} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4 }}>
        <Card data-testid="avg-session-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Avg Session
              </Typography>
              <TimerIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4" component="div">
              {formatDuration(summary.avgSessionDurationSeconds)}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Average session duration
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}
