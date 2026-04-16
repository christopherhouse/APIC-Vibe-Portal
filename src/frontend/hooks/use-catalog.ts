'use client';

import { useCallback, useEffect, useRef, useState, useTransition } from 'react';
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

  // Use a ref to hold the latest params so the callback always reads fresh values
  // without needing params in its dependency array.
  const paramsRef = useRef(params);
  paramsRef.current = params;

  // Stable key derived from primitive values to trigger refetch when params change
  const paramsKey = `${params.page}|${params.pageSize}|${params.sort}|${params.direction}|${params.lifecycle?.join(',')}|${params.kind?.join(',')}`;

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const data: CatalogListResponse = await fetchCatalogApis(paramsRef.current);
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
  }, [paramsKey]);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...state, isLoading: state.isLoading || isPending, refetch: load };
}
