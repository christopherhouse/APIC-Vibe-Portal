'use client';

import { Box, Typography } from '@mui/material';
import type { Recommendation } from '@/lib/metadata-api';
import RecommendationCard from './RecommendationCard';

interface RecommendationListProps {
  recommendations: Recommendation[];
}

export default function RecommendationList({ recommendations }: RecommendationListProps) {
  if (recommendations.length === 0) {
    return (
      <Box data-testid="recommendations-list-empty" sx={{ py: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          🎉 Great job! No recommendations — this API has excellent metadata.
        </Typography>
      </Box>
    );
  }

  return (
    <Box data-testid="recommendations-list">
      <Typography variant="h6" gutterBottom>
        Recommendations ({recommendations.length})
      </Typography>
      {recommendations.map((rec) => (
        <RecommendationCard key={rec.id} recommendation={rec} />
      ))}
    </Box>
  );
}
