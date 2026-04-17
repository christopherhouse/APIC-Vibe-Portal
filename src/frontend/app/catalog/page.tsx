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
import { useAuth } from '@/lib/auth/use-auth';

import ApiCatalogGrid from './components/ApiCatalogGrid';
import CatalogFilters from './components/CatalogFilters';
import CatalogSort, { type SortField, type SortDirection } from './components/CatalogSort';
import CatalogPagination from './components/CatalogPagination';
import ViewToggle, { type ViewMode } from './components/ViewToggle';

const FILTER_DRAWER_WIDTH = 260;

/** Allowed page size values. */
const ALLOWED_PAGE_SIZES = [10, 20, 50] as const;

/** Valid sort fields. */
const VALID_SORT_FIELDS: SortField[] = ['name', 'updatedAt', 'createdAt'];

/** Valid sort directions. */
const VALID_SORT_DIRECTIONS: SortDirection[] = ['asc', 'desc'];

/** Read view-mode preference from localStorage (client only). */
function getStoredViewMode(): ViewMode {
  if (typeof window === 'undefined') return 'grid';
  const stored = localStorage.getItem('catalog-view-mode');
  return stored === 'grid' || stored === 'list' ? stored : 'grid';
}

export default function CatalogPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { isAuthenticated } = useAuth();

  // ---------- state from URL (validated / clamped) ----------
  const rawPage = Number(searchParams.get('page') ?? '1');
  const page = Number.isFinite(rawPage) ? Math.max(1, Math.round(rawPage)) : 1;

  const rawPageSize = Number(searchParams.get('pageSize') ?? '10');
  const pageSize = ALLOWED_PAGE_SIZES.includes(rawPageSize as (typeof ALLOWED_PAGE_SIZES)[number])
    ? rawPageSize
    : 10;

  const rawSort = searchParams.get('sort') ?? 'name';
  const sort: SortField = VALID_SORT_FIELDS.includes(rawSort as SortField)
    ? (rawSort as SortField)
    : 'name';

  const rawDirection = searchParams.get('direction') ?? 'asc';
  const direction: SortDirection = VALID_SORT_DIRECTIONS.includes(rawDirection as SortDirection)
    ? (rawDirection as SortDirection)
    : 'asc';

  // BFF accepts a single lifecycle and a single kind value
  const lifecycle = searchParams.get('lifecycle') ?? undefined;
  const kind = searchParams.get('kind') ?? undefined;

  // ---------- local UI state ----------
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  // Initialise from localStorage on mount
  useEffect(() => {
    setViewMode(getStoredViewMode());
  }, []);

  // ---------- data fetching ----------
  const params = useMemo<CatalogListParams>(
    () => ({
      page,
      pageSize,
      sort,
      direction,
      lifecycle,
      kind,
    }),
    [page, pageSize, sort, direction, lifecycle, kind]
  );
  const { items, pagination, isLoading, error } = useCatalog({
    ...params,
    enabled: isAuthenticated,
  });

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
  const handlePageSizeChange = (newSize: number) =>
    updateSearch({ pageSize: String(newSize), page: '1' });
  const handleSortChange = (s: SortField, d: SortDirection) =>
    updateSearch({ sort: s, direction: d, page: '1' });
  const handleLifecycleChange = (value: string | undefined) =>
    updateSearch({ lifecycle: value, page: '1' });
  const handleKindChange = (value: string | undefined) => updateSearch({ kind: value, page: '1' });
  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem('catalog-view-mode', mode);
  };

  // ---------- filter sidebar content ----------
  const filterContent = (
    <CatalogFilters
      selectedLifecycle={lifecycle}
      selectedKind={kind}
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
