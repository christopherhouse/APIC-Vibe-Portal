import { ApiKind } from '../enums/api-kind.js';
import { ApiLifecycle } from '../enums/api-lifecycle.js';
import { PaginationParams } from '../models/pagination.js';

/**
 * Filters available for search queries.
 */
export interface SearchFilters {
  kind?: ApiKind[];
  lifecycleStage?: ApiLifecycle[];
  tags?: string[];
}

/**
 * Sort options for search results.
 */
export type SearchSortField = 'relevance' | 'name' | 'updatedAt' | 'createdAt';
export type SearchSortOrder = 'asc' | 'desc';

/**
 * Request DTO for the search endpoint.
 */
export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  sortBy?: SearchSortField;
  sortOrder?: SearchSortOrder;
  pagination?: PaginationParams;
}
