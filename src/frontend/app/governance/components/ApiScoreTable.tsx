'use client';

import { useState, useMemo } from 'react';
import {
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from '@mui/material';
import { useRouter } from 'next/navigation';
import type { ApiGovernanceScore } from '@/lib/governance-api';

interface ApiScoreTableProps {
  scores: ApiGovernanceScore[];
}

type SortField = 'apiName' | 'score' | 'category' | 'criticalFailures';
type SortDirection = 'asc' | 'desc';

export default function ApiScoreTable({ scores }: ApiScoreTableProps) {
  const router = useRouter();
  const [sortField, setSortField] = useState<SortField>('score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [filterText, setFilterText] = useState('');

  const getCategoryColor = (
    category: string
  ): 'success' | 'primary' | 'warning' | 'error' | 'default' => {
    switch (category) {
      case 'Excellent':
        return 'success';
      case 'Good':
        return 'primary';
      case 'Needs Improvement':
        return 'warning';
      case 'Poor':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const filteredAndSortedScores = useMemo(() => {
    let result = [...scores];

    // Filter
    if (filterText) {
      const lowerFilter = filterText.toLowerCase();
      result = result.filter(
        (score) =>
          score.apiName.toLowerCase().includes(lowerFilter) ||
          score.apiId.toLowerCase().includes(lowerFilter) ||
          score.category.toLowerCase().includes(lowerFilter)
      );
    }

    // Sort
    result.sort((a, b) => {
      let aValue: string | number = a[sortField];
      let bValue: string | number = b[sortField];

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = (bValue as string).toLowerCase();
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [scores, filterText, sortField, sortDirection]);

  if (scores.length === 0) {
    return (
      <Paper sx={{ p: 3 }} data-testid="api-score-table-empty">
        <Typography variant="body1" color="text.secondary" align="center">
          No API governance scores available
        </Typography>
      </Paper>
    );
  }

  return (
    <Box data-testid="api-score-table">
      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          label="Filter APIs"
          variant="outlined"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Search by API name, ID, or category"
          data-testid="api-score-table-filter"
        />
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'apiName'}
                  direction={sortField === 'apiName' ? sortDirection : 'asc'}
                  onClick={() => handleSort('apiName')}
                >
                  API Name
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'score'}
                  direction={sortField === 'score' ? sortDirection : 'asc'}
                  onClick={() => handleSort('score')}
                >
                  Score
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'category'}
                  direction={sortField === 'category' ? sortDirection : 'asc'}
                  onClick={() => handleSort('category')}
                >
                  Category
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'criticalFailures'}
                  direction={sortField === 'criticalFailures' ? sortDirection : 'asc'}
                  onClick={() => handleSort('criticalFailures')}
                >
                  Critical Issues
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredAndSortedScores.map((score) => (
              <TableRow
                key={score.apiId}
                hover
                onClick={() => router.push(`/governance/${score.apiId}`)}
                sx={{ cursor: 'pointer' }}
                data-testid={`api-score-row-${score.apiId}`}
              >
                <TableCell>{score.apiName}</TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">
                    {score.score.toFixed(1)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={score.category}
                    color={getCategoryColor(score.category)}
                    size="small"
                  />
                </TableCell>
                <TableCell>{score.criticalFailures}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {filteredAndSortedScores.length === 0 && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No APIs match your filter
          </Typography>
        </Box>
      )}
    </Box>
  );
}
