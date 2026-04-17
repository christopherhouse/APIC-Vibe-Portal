'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { SuggestItem } from '@/lib/search-api';
import { fetchSuggestions } from '@/lib/search-api';

export interface AutocompleteState {
  suggestions: SuggestItem[];
  isLoading: boolean;
  error: string | null;
}

export interface UseAutocompleteOptions {
  query: string;
  /** Minimum characters before triggering a request. Defaults to 2. */
  minChars?: number;
  /** Debounce delay in ms. Defaults to 300. */
  debounceMs?: number;
  /** When false the hook skips API calls. */
  enabled?: boolean;
}

/**
 * React hook for debounced, cancellable autocomplete suggestions.
 *
 * Only fires when the query is >= `minChars` characters long.
 */
export function useAutocomplete({
  query,
  minChars = 2,
  debounceMs = 300,
  enabled = true,
}: UseAutocompleteOptions): AutocompleteState {
  const [state, setState] = useState<AutocompleteState>({
    suggestions: [],
    isLoading: false,
    error: null,
  });

  const abortRef = useRef<AbortController | null>(null);

  const doFetch = useCallback(async (prefix: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const data = await fetchSuggestions(prefix, controller.signal);
      if (controller.signal.aborted) return;
      setState({ suggestions: data.suggestions, isLoading: false, error: null });
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setState({ suggestions: [], isLoading: false, error: null });
    }
  }, []);

  useEffect(() => {
    if (!enabled || query.trim().length < minChars) {
      abortRef.current?.abort();
      setState({ suggestions: [], isLoading: false, error: null });
      return;
    }

    const timerId = setTimeout(() => {
      void doFetch(query.trim());
    }, debounceMs);

    return () => clearTimeout(timerId);
  }, [query, minChars, debounceMs, enabled, doFetch]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return state;
}
