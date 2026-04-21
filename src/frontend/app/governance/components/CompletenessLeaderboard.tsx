'use client';

import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Grid,
  Box,
} from '@mui/material';
import { useRouter } from 'next/navigation';
import type { LeaderboardData } from '@/lib/metadata-api';

interface CompletenessLeaderboardProps {
  leaderboard: LeaderboardData;
}

const GRADE_COLORS: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  A: 'success',
  B: 'success',
  C: 'warning',
  D: 'error',
  F: 'error',
};

function LeaderboardTable({
  title,
  entries,
  testId,
  onRowClick,
}: {
  title: string;
  entries: { apiId: string; apiName: string; score: number; grade: string }[];
  testId: string;
  onRowClick: (apiId: string) => void;
}) {
  return (
    <Card variant="outlined" data-testid={testId}>
      <CardContent>
        <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
          {title}
        </Typography>
        {entries.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No data available
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>API</TableCell>
                  <TableCell align="right">Score</TableCell>
                  <TableCell align="right">Grade</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {entries.map((entry) => (
                  <TableRow
                    key={entry.apiId}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => onRowClick(entry.apiId)}
                    data-testid={`leaderboard-row-${entry.apiId}`}
                  >
                    <TableCell>{entry.apiName}</TableCell>
                    <TableCell align="right">{entry.score.toFixed(1)}</TableCell>
                    <TableCell align="right">
                      <Chip
                        label={entry.grade}
                        color={GRADE_COLORS[entry.grade] || 'default'}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default function CompletenessLeaderboard({ leaderboard }: CompletenessLeaderboardProps) {
  const router = useRouter();
  const handleRowClick = (apiId: string) => {
    router.push(`/catalog/${encodeURIComponent(apiId)}`);
  };

  return (
    <Box data-testid="completeness-leaderboard">
      <Typography variant="h6" gutterBottom>
        Metadata Completeness Leaderboard
      </Typography>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <LeaderboardTable
            title="🏆 Top 5 Most Complete"
            entries={leaderboard.top}
            testId="leaderboard-top"
            onRowClick={handleRowClick}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <LeaderboardTable
            title="⚠️ Bottom 5 — Needs Improvement"
            entries={leaderboard.bottom}
            testId="leaderboard-bottom"
            onRowClick={handleRowClick}
          />
        </Grid>
      </Grid>
    </Box>
  );
}
