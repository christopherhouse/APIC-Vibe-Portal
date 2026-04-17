'use client';

import { useCallback, useEffect, useRef, useState, useTransition } from 'react';
import type { BffSearchResponse, SearchFilters, SearchMode } from '@/lib/search-api';
import { fetchSearch } from '@/lib/search-api';

export interface SearchState {
  results: BffSearchResponse['results'];
  totalCount: number;
  facets: BffSearchResponse['facets'];
  queryDuration: number;
  isLoading: boolean;
  error: string | null;
}

const DEFAULT_FACETS: BffSearchResponse['facets'] = {
  kind: [],
  lifecycle: [],
  tags: [],
};

const EMPTY_STATE: SearchState = {
  results: [],
  totalCount: 0,
  facets: DEFAULT_FACETS,
  queryDuration: 0,
  isLoading: false,
  error: null,
};

export interface UseSearchOptions {
  query: string;
  filters?: SearchFilters;
  page?: number;
  pageSize?: number;
  searchMode?: SearchMode;
  /** Debounce delay in ms. Defaults to 300. */
  debounceMs?: number;
  /** When false the hook skips the API call. */
  enabled?: boolean;
}

/**
 * React hook for performing debounced, cancellable search requests.
 *
 * - Debounces the query by `debounceMs` ms (default 300).
 * - Cancels the previous in-flight request when params change.
 * - Returns empty results when `enabled` is false.
 */
export function useSearch({
  query,
  filters,
  page = 1,
  pageSize = 10,
  searchMode = 'hybrid',
  debounceMs = 300,
  enabled = true,
}: UseSearchOptions): SearchState & { refetch: () => void } {
  const [state, setState] = useState<SearchState>({ ...EMPTY_STATE, isLoading: false });
  const [, startTransition] = useTransition();

  // Ref to the current AbortController so we can cancel inflight requests.
  const abortRef = useRef<AbortController | null>(null);

  // Keep latest params in a ref so the stable `doSearch` always reads fresh values.
  const paramsRef = useRef({ query, filters, page, pageSize, searchMode });
  paramsRef.current = { query, filters, page, pageSize, searchMode };

  // Stable key to trigger the effect and recreate `doSearch` when params change.
  const filtersKey = JSON.stringify(filters);
  const paramsKey = `${query}|${filtersKey}|${page}|${pageSize}|${searchMode}`;

  const doSearch = useCallback(async () => {
    // Cancel any previous request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    // Read the latest params from the ref so this callback is always up-to-date.
    const { query: q, filters: f, page: pg, pageSize: ps, searchMode: sm } = paramsRef.current;

    try {
      const data = await fetchSearch(
        { query: q, filters: f, page: pg, pageSize: ps, searchMode: sm },
        controller.signal
      );
      if (controller.signal.aborted) return;
      startTransition(() => {
        setState({
          results: data.results,
          totalCount: data.totalCount,
          facets: data.facets,
          queryDuration: data.queryDuration,
          isLoading: false,
          error: null,
        });
      });
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Search failed',
      }));
    }
  }, [paramsKey]); // re-create whenever params change so the effect picks up the new version

  useEffect(() => {
    if (!enabled || query.trim() === '') {
      setState(EMPTY_STATE);
      return;
    }

    const timerId = setTimeout(() => {
      void doSearch();
    }, debounceMs);

    return () => {
      clearTimeout(timerId);
    };
  }, [doSearch, enabled, query, debounceMs]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return { ...state, refetch: doSearch };
}
