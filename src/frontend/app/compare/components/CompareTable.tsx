'use client';

import React from 'react';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import type { CompareResponse } from '@/lib/compare-api';
import CompareAspectRow from './CompareAspectRow';

export interface CompareTableProps {
  result: CompareResponse;
}

export default function CompareTable({ result }: CompareTableProps) {
  const { apis, aspects } = result;

  // Group aspect rows by top-level category
  const grouped = aspects.reduce<Record<string, typeof aspects>>((acc, row) => {
    const category = row.aspect.split('.')[0];
    if (!acc[category]) acc[category] = [];
    acc[category].push(row);
    return acc;
  }, {});

  return (
    <Box data-testid="compare-table">
      {/* Similarity score */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Similarity score:
        </Typography>
        <Chip
          label={`${Math.round(result.similarityScore * 100)}%`}
          color={
            result.similarityScore >= 0.7
              ? 'success'
              : result.similarityScore >= 0.4
                ? 'warning'
                : 'default'
          }
          size="small"
        />
      </Box>

      <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto' }}>
        <Table size="small" stickyHeader>
          {/* Header: one column per API */}
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700, minWidth: 160 }}>Aspect</TableCell>
              {apis.map((api) => (
                <TableCell key={api.id} align="center" sx={{ fontWeight: 700, minWidth: 140 }}>
                  <Typography variant="subtitle2">{api.title}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {api.kind.toUpperCase()} · {api.lifecycleStage}
                  </Typography>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {Object.entries(grouped).map(([category, rows]) => (
              <React.Fragment key={category}>
                {/* Category sub-header */}
                <TableRow>
                  <TableCell
                    colSpan={apis.length + 1}
                    sx={{
                      backgroundColor: 'primary.main',
                      color: 'primary.contrastText',
                      fontWeight: 700,
                      textTransform: 'capitalize',
                      py: 0.5,
                    }}
                  >
                    {category}
                  </TableCell>
                </TableRow>

                {/* Aspect rows for this category */}
                {rows.map((row) => (
                  <CompareAspectRow key={row.aspect} row={row} />
                ))}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
