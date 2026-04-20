'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';

import { useAuth } from '@/lib/auth/use-auth';
import { compareApis, type CompareResponse } from '@/lib/compare-api';
import type { ApiCatalogItem } from '@apic-vibe-portal/shared';

import CompareEmptyState from './components/CompareEmptyState';
import CompareSelector from './components/CompareSelector';
import CompareTable from './components/CompareTable';
import CompareAiAnalysis from './components/CompareAiAnalysis';

const MIN_COMPARE = 2;

export default function ComparePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isAuthenticated } = useAuth();

  // Parse compare IDs from URL
  const compareParam = searchParams.get('compare') ?? '';
  const selectedIds = compareParam.split(',').filter(Boolean);

  const [result, setResult] = useState<CompareResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runComparison = useCallback(async (ids: string[]) => {
    if (ids.length < MIN_COMPARE) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await compareApis({ apiIds: ids });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare APIs');
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Re-run comparison whenever selected IDs change
  useEffect(() => {
    if (!isAuthenticated) return;
    if (selectedIds.length >= MIN_COMPARE) {
      void runComparison(selectedIds);
    } else {
      setResult(null);
    }
  }, [compareParam, isAuthenticated, runComparison, selectedIds]);

  // URL helpers
  const updateCompare = (ids: string[]) => {
    const sp = new URLSearchParams(searchParams.toString());
    if (ids.length === 0) {
      sp.delete('compare');
    } else {
      sp.set('compare', ids.join(','));
    }
    router.push(`/compare?${sp.toString()}`, { scroll: false });
  };

  const handleAdd = (api: ApiCatalogItem) => {
    if (selectedIds.includes(api.id)) return;
    updateCompare([...selectedIds, api.id]);
  };

  const handleRemove = (id: string) => {
    updateCompare(selectedIds.filter((x) => x !== id));
  };

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Page header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <CompareArrowsIcon color="primary" />
        <Typography variant="h4" component="h1">
          API Comparison
        </Typography>
      </Box>

      {/* API selector */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <CompareSelector selectedIds={selectedIds} onAdd={handleAdd} onRemove={handleRemove} />
      </Paper>

      {/* Loading state */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void runComparison(selectedIds)}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {/* Empty state */}
      {!isLoading && !result && !error && <CompareEmptyState />}

      {/* Comparison results */}
      {result && !isLoading && (
        <Box>
          <CompareTable result={result} />

          <Divider sx={{ my: 4 }} />

          <CompareAiAnalysis result={result} onAnalysisLoaded={(updated) => setResult(updated)} />
        </Box>
      )}
    </Container>
  );
}
