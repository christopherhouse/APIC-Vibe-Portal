'use client';

import { useCallback, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import FilterListIcon from '@mui/icons-material/FilterList';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import { useSearch } from '@/hooks/use-search';
import type { SearchMode } from '@/lib/search-api';
import type { ApiKind, ApiLifecycle } from '@apic-vibe-portal/shared';

import SearchResults from './components/SearchResults';
import SearchSummary from './components/SearchSummary';
import SearchModeToggle from './components/SearchModeToggle';
import SearchFilters from './components/SearchFilters';
import NoResults from './components/NoResults';

const FILTER_DRAWER_WIDTH = 280;

const VALID_MODES: SearchMode[] = ['keyword', 'semantic', 'hybrid'];

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // Parse URL state
  // ---------------------------------------------------------------------------
  const query = searchParams.get('q') ?? '';
  const kind = searchParams.get('kind') ?? undefined;
  const lifecycle = searchParams.get('lifecycle') ?? undefined;
  const rawMode = searchParams.get('mode') ?? 'hybrid';
  const searchMode: SearchMode = VALID_MODES.includes(rawMode as SearchMode)
    ? (rawMode as SearchMode)
    : 'hybrid';
  const rawPage = Number(searchParams.get('page') ?? '1');
  const page = Number.isFinite(rawPage) && Number.isInteger(rawPage) ? Math.max(1, rawPage) : 1;

  // ---------------------------------------------------------------------------
  // Build filters for the hook
  // ---------------------------------------------------------------------------
  const filters = useMemo(
    () => ({
      kind: kind ? ([kind] as ApiKind[]) : undefined,
      lifecycle: lifecycle ? ([lifecycle] as ApiLifecycle[]) : undefined,
    }),
    [kind, lifecycle]
  );

  // ---------------------------------------------------------------------------
  // Search hook
  // ---------------------------------------------------------------------------
  const { results, totalCount, facets, queryDuration, isLoading, error } = useSearch({
    query,
    filters,
    page,
    pageSize: 10,
    searchMode,
    enabled: query.trim().length > 0,
  });

  // ---------------------------------------------------------------------------
  // URL helpers
  // ---------------------------------------------------------------------------
  const updateSearch = useCallback(
    (updates: Record<string, string | undefined>) => {
      const sp = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (value === undefined) {
          sp.delete(key);
        } else {
          sp.set(key, value);
        }
      });
      router.push(`/search?${sp.toString()}`);
    },
    [router, searchParams]
  );

  const handleLifecycleChange = (value: string | undefined) =>
    updateSearch({ lifecycle: value, page: '1' });

  const handleKindChange = (value: string | undefined) => updateSearch({ kind: value, page: '1' });

  const handleModeChange = (mode: SearchMode) => updateSearch({ mode, page: '1' });

  // ---------------------------------------------------------------------------
  // Filter sidebar content
  // ---------------------------------------------------------------------------
  const filterContent = (
    <SearchFilters
      selectedLifecycle={lifecycle}
      selectedKind={kind}
      facets={facets}
      onLifecycleChange={handleLifecycleChange}
      onKindChange={handleKindChange}
    />
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  const showNoResults = !isLoading && !error && query.trim().length > 0 && results.length === 0;
  const showResults = !isLoading && !error && results.length > 0;
  const showEmptyQuery = !query.trim();

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Page header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Search
        </Typography>
        {query && (
          <SearchSummary query={query} totalCount={totalCount} queryDuration={queryDuration} />
        )}
      </Box>

      {/* Toolbar */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        {isMobile && (
          <IconButton aria-label="Open filters" onClick={() => setFilterDrawerOpen(true)}>
            <FilterListIcon />
          </IconButton>
        )}
        <SearchModeToggle mode={searchMode} onChange={handleModeChange} />
      </Box>

      {/* Content area */}
      <Box sx={{ display: 'flex', gap: 3 }}>
        {/* Desktop filter sidebar */}
        {!isMobile && <Box sx={{ width: FILTER_DRAWER_WIDTH, flexShrink: 0 }}>{filterContent}</Box>}

        {/* Mobile filter drawer */}
        {isMobile && (
          <Drawer
            anchor="left"
            open={filterDrawerOpen}
            onClose={() => setFilterDrawerOpen(false)}
            slotProps={{ paper: { sx: { width: FILTER_DRAWER_WIDTH, p: 2, pt: 3 } } }}
          >
            {filterContent}
          </Drawer>
        )}

        {/* Main results area */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {showEmptyQuery && (
            <Box sx={{ py: 8, textAlign: 'center' }}>
              <Typography variant="h6" color="text.secondary">
                Enter a search query above to find APIs
              </Typography>
            </Box>
          )}

          {(isLoading || showResults) && <SearchResults results={results} isLoading={isLoading} />}

          {showNoResults && <NoResults query={query} />}
        </Box>
      </Box>
    </Container>
  );
}
