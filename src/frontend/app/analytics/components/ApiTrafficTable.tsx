'use client';

import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
} from '@mui/material';
import { useState, useMemo } from 'react';
import type { PopularApi } from '@/lib/analytics-api';

interface ApiTrafficTableProps {
  apis: PopularApi[];
}

type SortField = 'apiName' | 'viewCount' | 'downloadCount' | 'chatMentionCount';
type SortDirection = 'asc' | 'desc';

export default function ApiTrafficTable({ apis }: ApiTrafficTableProps) {
  const [sortField, setSortField] = useState<SortField>('viewCount');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedApis = useMemo(() => {
    return [...apis].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal);
      }
      return sortDirection === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [apis, sortField, sortDirection]);

  if (apis.length === 0) {
    return (
      <Paper sx={{ p: 3 }} data-testid="api-traffic-table-empty">
        <Typography variant="body1" color="text.secondary" align="center">
          No API traffic data available
        </Typography>
      </Paper>
    );
  }

  return (
    <Box data-testid="api-traffic-table">
      <TableContainer component={Paper}>
        <Table size="small">
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
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'viewCount'}
                  direction={sortField === 'viewCount' ? sortDirection : 'asc'}
                  onClick={() => handleSort('viewCount')}
                >
                  Views
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'downloadCount'}
                  direction={sortField === 'downloadCount' ? sortDirection : 'asc'}
                  onClick={() => handleSort('downloadCount')}
                >
                  Downloads
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'chatMentionCount'}
                  direction={sortField === 'chatMentionCount' ? sortDirection : 'asc'}
                  onClick={() => handleSort('chatMentionCount')}
                >
                  Chat Mentions
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedApis.map((api) => (
              <TableRow key={api.apiId} data-testid={`api-traffic-row-${api.apiId}`}>
                <TableCell>{api.apiName}</TableCell>
                <TableCell align="right">{api.viewCount.toLocaleString()}</TableCell>
                <TableCell align="right">{api.downloadCount.toLocaleString()}</TableCell>
                <TableCell align="right">{api.chatMentionCount.toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
