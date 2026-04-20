'use client';

import { Box, Card, CardContent, Grid, Typography } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import type { GovernanceSummary } from '@/lib/governance-api';

interface GovernanceOverviewProps {
  summary: GovernanceSummary;
}

export default function GovernanceOverview({ summary }: GovernanceOverviewProps) {
  const getTrendIcon = (value: number) => {
    if (value > 0) return <TrendingUpIcon color="success" />;
    if (value < 0) return <TrendingDownIcon color="error" />;
    return <TrendingFlatIcon color="disabled" />;
  };

  const compliancePercentage =
    summary.totalCount > 0 ? Math.round((summary.compliantCount / summary.totalCount) * 100) : 0;

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} sm={6} md={3}>
        <Card data-testid="overall-score-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Overall Score
              </Typography>
              {getTrendIcon(summary.improvement)}
            </Box>
            <Typography variant="h3" component="div">
              {summary.overallScore.toFixed(1)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {summary.improvement > 0 && '+'}
              {summary.improvement.toFixed(1)} over last 30 days
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card data-testid="compliant-apis-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Compliant APIs
              </Typography>
              <CheckCircleIcon color="success" />
            </Box>
            <Typography variant="h3" component="div">
              {summary.compliantCount}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {compliancePercentage}% of {summary.totalCount} APIs (≥75 score)
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card data-testid="critical-issues-card">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography color="text.secondary" variant="body2" sx={{ flexGrow: 1 }}>
                Critical Issues
              </Typography>
              <WarningIcon color="error" />
            </Box>
            <Typography variant="h3" component="div">
              {summary.criticalIssues}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              APIs with critical rule failures
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card data-testid="total-apis-card">
          <CardContent>
            <Typography color="text.secondary" variant="body2" gutterBottom>
              Total APIs
            </Typography>
            <Typography variant="h3" component="div">
              {summary.totalCount}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Tracked for governance
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}
