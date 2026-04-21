'use client';

import { Box, Card, CardContent, Typography, CircularProgress } from '@mui/material';
import type { CompletenessScoreData } from '@/lib/metadata-api';

interface CompletenessScoreProps {
  score: CompletenessScoreData;
}

const GRADE_COLORS: Record<string, string> = {
  A: '#2e7d32',
  B: '#1b5e20',
  C: '#f57f17',
  D: '#e65100',
  F: '#c62828',
};

export default function CompletenessScore({ score }: CompletenessScoreProps) {
  const gradeColor = GRADE_COLORS[score.grade] || GRADE_COLORS.F;

  return (
    <Card data-testid="completeness-score-card">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Metadata Quality Score
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, my: 2 }}>
          <Box sx={{ position: 'relative', display: 'inline-flex' }}>
            <CircularProgress
              variant="determinate"
              value={score.overallScore}
              size={100}
              thickness={6}
              sx={{ color: gradeColor }}
              data-testid="score-progress"
            />
            <Box
              sx={{
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
              }}
            >
              <Typography
                variant="h4"
                component="div"
                sx={{ fontWeight: 'bold', color: gradeColor }}
              >
                {score.grade}
              </Typography>
            </Box>
          </Box>
          <Box>
            <Typography variant="h4" component="div">
              {score.overallScore.toFixed(1)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              out of 100
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}
