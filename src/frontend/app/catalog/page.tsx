'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import FilterListIcon from '@mui/icons-material/FilterList';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';

import { useCatalog } from '@/hooks/use-catalog';
import type { CatalogListParams } from '@/lib/catalog-api';

import ApiCatalogGrid from './components/ApiCatalogGrid';
import CatalogFilters from './components/CatalogFilters';
import CatalogSort, { type SortField, type SortDirection } from './components/CatalogSort';
import CatalogPagination from './components/CatalogPagination';
import ViewToggle, { type ViewMode } from './components/ViewToggle';

const FILTER_DRAWER_WIDTH = 260;

/** Read view-mode preference from localStorage (client only). */
function getStoredViewMode(): ViewMode {
  if (typeof window === 'undefined') return 'grid';
  return (localStorage.getItem('catalog-view-mode') as ViewMode) ?? 'grid';
}

export default function CatalogPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // ---------- state from URL ----------
  const page = Number(searchParams.get('page') ?? '1');
  const pageSize = Number(searchParams.get('pageSize') ?? '20');
  const sort = (searchParams.get('sort') ?? 'updatedAt') as SortField;
  const direction = (searchParams.get('direction') ?? 'desc') as SortDirection;
  const lifecycles = searchParams.getAll('lifecycle');
  const kinds = searchParams.getAll('kind');

  // ---------- local UI state ----------
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  // Initialise from localStorage on mount
  useEffect(() => {
    setViewMode(getStoredViewMode());
  }, []);

  // ---------- data fetching ----------
  // Serialize array values for stable useMemo dependencies
  const lifecyclesKey = lifecycles.join(',');
  const kindsKey = kinds.join(',');
  const params = useMemo<CatalogListParams>(
    () => ({
      page,
      pageSize,
      sort,
      direction,
      lifecycle: lifecyclesKey ? lifecyclesKey.split(',') : [],
      kind: kindsKey ? kindsKey.split(',') : [],
    }),
    [page, pageSize, sort, direction, lifecyclesKey, kindsKey]
  );
  const { items, pagination, isLoading, error } = useCatalog(params);

  // ---------- URL update helper ----------
  const updateSearch = useCallback(
    (updates: Record<string, string | string[] | undefined>) => {
      const sp = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        sp.delete(key);
        if (value === undefined) return;
        if (Array.isArray(value)) {
          value.forEach((v) => sp.append(key, v));
        } else {
          sp.set(key, value);
        }
      });
      router.push(`/catalog?${sp.toString()}`);
    },
    [router, searchParams]
  );

  // ---------- event handlers ----------
  const handlePageChange = (newPage: number) => updateSearch({ page: String(newPage) });
  const handlePageSizeChange = (newSize: number) => updateSearch({ pageSize: String(newSize), page: '1' });
  const handleSortChange = (s: SortField, d: SortDirection) => updateSearch({ sort: s, direction: d, page: '1' });
  const handleLifecycleChange = (values: string[]) => updateSearch({ lifecycle: values.length ? values : undefined, page: '1' });
  const handleKindChange = (values: string[]) => updateSearch({ kind: values.length ? values : undefined, page: '1' });
  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem('catalog-view-mode', mode);
  };

  // ---------- filter sidebar content ----------
  const filterContent = (
    <CatalogFilters
      selectedLifecycles={lifecycles}
      selectedKinds={kinds}
      onLifecycleChange={handleLifecycleChange}
      onKindChange={handleKindChange}
    />
  );

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Page header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          API Catalog
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Browse and discover APIs available in your organization.
        </Typography>
      </Box>

      {/* Toolbar */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        {isMobile && (
          <IconButton aria-label="Open filters" onClick={() => setFilterDrawerOpen(true)}>
            <FilterListIcon />
          </IconButton>
        )}
        <CatalogSort sort={sort} direction={direction} onSortChange={handleSortChange} />
        <Box sx={{ flex: 1 }} />
        <ViewToggle viewMode={viewMode} onChange={handleViewModeChange} />
      </Box>

      {/* Content area */}
      <Box sx={{ display: 'flex', gap: 3 }}>
        {/* Desktop filter sidebar */}
        {!isMobile && (
          <Box sx={{ width: FILTER_DRAWER_WIDTH, flexShrink: 0 }}>
            {filterContent}
          </Box>
        )}

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

        {/* Main content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {isLoading ? (
            <CatalogSkeleton viewMode={viewMode} />
          ) : (
            <ApiCatalogGrid items={items} viewMode={viewMode} />
          )}

          <CatalogPagination
            pagination={pagination}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        </Box>
      </Box>
    </Container>
  );
}

/** Skeleton placeholder while data is loading. */
function CatalogSkeleton({ viewMode }: { viewMode: ViewMode }) {
  const count = 6;
  if (viewMode === 'list') {
    return (
      <Box data-testid="catalog-skeleton">
        {Array.from({ length: count }, (_, i) => (
          <Skeleton key={i} variant="rounded" height={56} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  return (
    <Box
      data-testid="catalog-skeleton"
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' },
        gap: 3,
      }}
    >
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} variant="rounded" height={200} />
      ))}
    </Box>
  );
}
