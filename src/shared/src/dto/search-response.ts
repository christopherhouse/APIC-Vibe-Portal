import { ApiCatalogItem } from './api-catalog-response.js';
import { SearchResult } from '../models/search-result.js';

/**
 * Response DTO for the search endpoint.
 * Uses the generic SearchResult with API catalog items.
 */
export type SearchResponse = SearchResult<ApiCatalogItem>;
