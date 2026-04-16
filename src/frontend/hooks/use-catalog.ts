'use client';

import { useCallback, useEffect, useState, useTransition } from 'react';
import type { ApiCatalogItem, PaginationMeta } from '@apic-vibe-portal/shared';
import {
  fetchCatalogApis,
  type CatalogListParams,
  type CatalogListResponse,
} from '@/lib/catalog-api';

export interface CatalogState {
  items: ApiCatalogItem[];
  pagination: PaginationMeta;
  isLoading: boolean;
  error: string | null;
}

const DEFAULT_PAGINATION: PaginationMeta = {
  page: 1,
  pageSize: 20,
  totalCount: 0,
  totalPages: 0,
};

/**
 * React hook for client-side catalog data fetching.
 *
 * Accepts filter / sort / pagination params and refetches whenever they change.
 */
export function useCatalog(params: CatalogListParams) {
  const [state, setState] = useState<CatalogState>({
    items: [],
    pagination: DEFAULT_PAGINATION,
    isLoading: true,
    error: null,
  });

  const [isPending, startTransition] = useTransition();

  // Serialize params for stable useCallback dependency
  const paramsKey = JSON.stringify(params);

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const fetchParams: CatalogListParams = JSON.parse(paramsKey);
      const data: CatalogListResponse = await fetchCatalogApis(fetchParams);
      startTransition(() => {
        setState({
          items: data.data,
          pagination: data.meta,
          isLoading: false,
          error: null,
        });
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load APIs',
      }));
    }
  }, [paramsKey]); // stable string dependency

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, isLoading: state.isLoading || isPending, refetch: load };
}
