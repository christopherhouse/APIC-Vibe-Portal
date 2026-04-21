'use client';

import { useEffect, useState, useCallback } from 'react';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import {
  fetchCompletenessScore,
  fetchRecommendations,
  type CompletenessScoreData,
  type Recommendation,
} from '@/lib/metadata-api';
import CompletenessScore from './CompletenessScore';
import CompletenessBreakdown from './CompletenessBreakdown';
import RecommendationList from './RecommendationList';

interface MetadataQualityTabProps {
  apiId: string;
}

export default function MetadataQualityTab({ apiId }: MetadataQualityTabProps) {
  const [scoreData, setScoreData] = useState<CompletenessScoreData | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [score, recs] = await Promise.all([
        fetchCompletenessScore(apiId),
        fetchRecommendations(apiId),
      ]);
      setScoreData(score);
      setRecommendations(recs.recommendations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load metadata quality data');
    } finally {
      setLoading(false);
    }
  }, [apiId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress data-testid="metadata-quality-loading" />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert
        severity="error"
        data-testid="metadata-quality-error"
        action={
          <Button color="inherit" size="small" onClick={() => void loadData()}>
            Retry
          </Button>
        }
      >
        {error}
      </Alert>
    );
  }

  if (!scoreData) {
    return (
      <Alert severity="info" data-testid="metadata-quality-empty">
        No metadata quality data available for this API.
      </Alert>
    );
  }

  return (
    <Box data-testid="metadata-quality-tab" sx={{ py: 2 }}>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 5 }}>
          <CompletenessScore score={scoreData} />
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}>
          <CompletenessBreakdown dimensions={scoreData.dimensions} />
        </Grid>
      </Grid>
      <Box sx={{ mt: 3 }}>
        <RecommendationList recommendations={recommendations} />
      </Box>
    </Box>
  );
}
