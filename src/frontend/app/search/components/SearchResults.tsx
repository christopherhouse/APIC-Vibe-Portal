'use client';

import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';
import type { SearchResultItem } from '@/lib/search-api';
import SearchResultCard from './SearchResultCard';

export interface SearchResultsProps {
  results: SearchResultItem[];
  isLoading: boolean;
}

function ResultSkeleton() {
  return (
    <Box sx={{ mb: 2 }} data-testid="search-result-skeleton">
      <Skeleton variant="rounded" height={140} />
    </Box>
  );
}

export default function SearchResults({ results, isLoading }: SearchResultsProps) {
  if (isLoading) {
    return (
      <Box data-testid="search-results-loading">
        {Array.from({ length: 5 }, (_, i) => (
          <ResultSkeleton key={i} />
        ))}
      </Box>
    );
  }

  return (
    <Box data-testid="search-results">
      {results.map((result) => (
        <SearchResultCard key={result.apiId} result={result} />
      ))}
    </Box>
  );
}
