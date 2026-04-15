/**
 * Pagination request parameters.
 */
export interface PaginationParams {
  page: number;
  pageSize: number;
}

/**
 * Pagination metadata returned in responses.
 */
export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

/**
 * Generic paginated response wrapper.
 */
export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}
