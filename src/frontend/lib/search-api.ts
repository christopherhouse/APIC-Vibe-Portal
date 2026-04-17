/**
 * Search API client functions for the APIC Vibe Portal.
 *
 * Wraps the BFF search endpoints:
 *   POST /api/search          — full hybrid search with facets
 *   GET  /api/search/suggest  — autocomplete prefix suggestions
 */

import type {
  ApiKind,
  ApiLifecycle,
  SearchFilters as SharedSearchFilters,
  PaginationParams,
} from '@apic-vibe-portal/shared';
import { apiClient } from '@/lib/api-client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SearchMode = 'keyword' | 'semantic' | 'hybrid';

export interface SearchResultHighlights {
  title?: string[];
  description?: string[];
}

/** A single API result returned by the search endpoint. */
export interface SearchResultItem {
  apiId: string;
  apiName: string;
  title: string;
  description: string;
  kind: ApiKind;
  lifecycleStage: ApiLifecycle;
  score: number;
  highlights?: SearchResultHighlights;
  /** AI-generated relevance caption (hybrid/semantic modes). */
  semanticCaption?: string;
}

export interface SearchFacetValue {
  value: string;
  count: number;
}

export interface SearchFacets {
  kind: SearchFacetValue[];
  lifecycle: SearchFacetValue[];
  tags: SearchFacetValue[];
}

/**
 * Re-export the shared SearchFilters type so consumers import from one place.
 * Uses `lifecycleStage` (not `lifecycle`) to match the shared DTO.
 */
export type SearchFilters = SharedSearchFilters;

/**
 * Search request DTO aligned with the shared SearchRequest shape.
 * Pagination is nested under `pagination: { page, pageSize }`.
 */
export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  pagination?: PaginationParams;
  searchMode?: SearchMode;
}

export interface BffSearchResponse {
  results: SearchResultItem[];
  totalCount: number;
  facets: SearchFacets;
  queryDuration: number;
}

export interface SuggestItem {
  apiId: string;
  title: string;
  description: string;
  kind: ApiKind;
}

export interface SuggestResponse {
  suggestions: SuggestItem[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Execute a full search against the BFF.
 * Accepts an optional AbortSignal for request cancellation.
 */
export async function fetchSearch(
  request: SearchRequest,
  signal?: AbortSignal
): Promise<BffSearchResponse> {
  return apiClient.post<BffSearchResponse>('/api/search', request, { signal });
}

/**
 * Fetch autocomplete suggestions for a given prefix.
 * Accepts an optional AbortSignal for request cancellation.
 */
export async function fetchSuggestions(
  prefix: string,
  signal?: AbortSignal
): Promise<SuggestResponse> {
  return apiClient.get<SuggestResponse>('/api/search/suggest', {
    params: { q: prefix },
    signal,
  });
}
