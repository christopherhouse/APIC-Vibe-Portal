'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export interface SearchSummaryProps {
  query: string;
  totalCount: number;
  queryDuration: number;
}

export default function SearchSummary({ query, totalCount, queryDuration }: SearchSummaryProps) {
  return (
    <Box data-testid="search-summary" sx={{ mb: 2 }}>
      <Typography variant="body2" color="text.secondary">
        {totalCount === 0 ? (
          'No results found'
        ) : (
          <>
            <strong>{totalCount.toLocaleString()}</strong> result
            {totalCount !== 1 ? 's' : ''} for{' '}
            <Box component="span" sx={{ fontStyle: 'italic' }}>
              &ldquo;{query}&rdquo;
            </Box>{' '}
            <Box component="span" color="text.disabled">
              ({queryDuration}ms)
            </Box>
          </>
        )}
      </Typography>
    </Box>
  );
}
