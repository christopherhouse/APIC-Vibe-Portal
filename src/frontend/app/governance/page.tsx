'use client';

import { useEffect, useState, useCallback } from 'react';
import { Box, Container, Typography, Alert, CircularProgress, Button, Grid } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import GovernanceOverview from './components/GovernanceOverview';
import ScoreDistributionChart from './components/ScoreDistributionChart';
import RuleComplianceChart from './components/RuleComplianceChart';
import ApiScoreTable from './components/ApiScoreTable';
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

export default function GovernancePage() {
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [scores, setScores] = useState<ApiGovernanceScore[]>([]);
  const [distribution, setDistribution] = useState<ScoreDistribution | null>(null);
  const [ruleCompliance, setRuleCompliance] = useState<RuleCompliance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, scoresData, distributionData, complianceData] = await Promise.all([
        fetchGovernanceSummary(),
        fetchGovernanceScores(),
        fetchScoreDistribution(),
        fetchRuleCompliance(),
      ]);
      setSummary(summaryData);
      setScores(scoresData);
      setDistribution(distributionData);
      setRuleCompliance(complianceData);
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
        <Grid item xs={12} md={6}>
          <ScoreDistributionChart distribution={distribution} />
        </Grid>
        <Grid item xs={12} md={6}>
          <RuleComplianceChart compliance={ruleCompliance} />
        </Grid>
      </Grid>

      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          API Governance Scores
        </Typography>
        <ApiScoreTable scores={scores} />
      </Box>
    </Container>
  );
}
