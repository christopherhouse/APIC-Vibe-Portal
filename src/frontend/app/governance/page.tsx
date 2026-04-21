'use client';

import { useEffect, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Box, Container, Typography, Alert, CircularProgress, Button, Grid } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import GovernanceOverview from './components/GovernanceOverview';
import ApiScoreTable from './components/ApiScoreTable';
import CompletenessOverview from './components/CompletenessOverview';
import CompletenessLeaderboard from './components/CompletenessLeaderboard';
import {
  fetchGovernanceSummary,
  fetchGovernanceScores,
  fetchScoreDistribution,
  fetchRuleCompliance,
  type GovernanceSummary,
  type ApiGovernanceScore,
  type ScoreDistribution,
  type RuleCompliance,
} from '@/lib/governance-api';
import {
  fetchCompletenessOverview,
  fetchCompletenessLeaderboard,
  type CompletenessOverviewData,
  type LeaderboardData,
} from '@/lib/metadata-api';

// Lazy-load heavy Recharts-based chart components to reduce initial bundle size
const ScoreDistributionChart = dynamic(() => import('./components/ScoreDistributionChart'), {
  ssr: false,
  loading: () => <CircularProgress size={24} />,
});
const RuleComplianceChart = dynamic(() => import('./components/RuleComplianceChart'), {
  ssr: false,
  loading: () => <CircularProgress size={24} />,
});

export default function GovernancePage() {
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [scores, setScores] = useState<ApiGovernanceScore[]>([]);
  const [distribution, setDistribution] = useState<ScoreDistribution | null>(null);
  const [ruleCompliance, setRuleCompliance] = useState<RuleCompliance[]>([]);
  const [completenessOverview, setCompletenessOverview] = useState<CompletenessOverviewData | null>(
    null
  );
  const [leaderboard, setLeaderboard] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, scoresData, distributionData, complianceData, overviewData, boardData] =
        await Promise.all([
          fetchGovernanceSummary(),
          fetchGovernanceScores(),
          fetchScoreDistribution(),
          fetchRuleCompliance(),
          fetchCompletenessOverview(),
          fetchCompletenessLeaderboard(),
        ]);
      setSummary(summaryData);
      setScores(scoresData);
      setDistribution(distributionData);
      setRuleCompliance(complianceData);
      setCompletenessOverview(overviewData);
      setLeaderboard(boardData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load governance data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading && !summary) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress data-testid="governance-loading" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error" data-testid="governance-error">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!summary || !distribution) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="info">No governance data available</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }} data-testid="governance-dashboard">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1">
          Governance Dashboard
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadData}
          disabled={loading}
          data-testid="refresh-button"
        >
          Refresh
        </Button>
      </Box>

      <Box sx={{ mb: 4 }}>
        <GovernanceOverview summary={summary} />
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <ScoreDistributionChart distribution={distribution} />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <RuleComplianceChart compliance={ruleCompliance} />
        </Grid>
      </Grid>

      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          API Governance Scores
        </Typography>
        <ApiScoreTable scores={scores} />
      </Box>

      {completenessOverview && (
        <Box sx={{ mb: 4 }}>
          <CompletenessOverview overview={completenessOverview} />
        </Box>
      )}

      {leaderboard && (
        <Box sx={{ mb: 4 }}>
          <CompletenessLeaderboard leaderboard={leaderboard} />
        </Box>
      )}
    </Container>
  );
}
