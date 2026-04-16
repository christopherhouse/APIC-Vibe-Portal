/**
 * API catalog data fetching functions.
 *
 * These functions call the BFF `/api/catalog` endpoint and return typed
 * responses matching the shared types package.
 */

import type { ApiCatalogItem, PaginationMeta } from '@apic-vibe-portal/shared';
import { toApiCatalogItem } from '@apic-vibe-portal/shared';
import type { ApiDefinition } from '@apic-vibe-portal/shared';
import { apiClient } from '@/lib/api-client';

/** Parameters accepted by the catalog list endpoint. */
export interface CatalogListParams {
  page?: number;
  pageSize?: number;
  sort?: string;
  direction?: string;
  lifecycle?: string;
  kind?: string;
}

/** Shape of the BFF list-APIs response envelope. */
export interface CatalogListResponse {
  data: ApiCatalogItem[];
  meta: PaginationMeta;
}

/** Raw BFF response shape (returns ApiDefinition[], not ApiCatalogItem[]). */
interface BffCatalogResponse {
  data: ApiDefinition[];
  meta: PaginationMeta;
}

/**
 * Fetch a paginated, filtered, sorted list of APIs from the BFF.
 *
 * The BFF returns full `ApiDefinition` objects; this function maps them
 * to `ApiCatalogItem` summaries for the catalog listing UI.
 */
export async function fetchCatalogApis(
  params: CatalogListParams = {}
): Promise<CatalogListResponse> {
  const queryParams: Record<string, string> = {};

  if (params.page) queryParams['page'] = String(params.page);
  if (params.pageSize) queryParams['pageSize'] = String(params.pageSize);
  if (params.sort) queryParams['sort'] = params.sort;
  if (params.direction) queryParams['direction'] = params.direction;
  if (params.lifecycle) queryParams['lifecycle'] = params.lifecycle;
  if (params.kind) queryParams['kind'] = params.kind;

  const raw = await apiClient.get<BffCatalogResponse>('/api/catalog', {
    params: queryParams,
  });

  return {
    data: raw.data.map(toApiCatalogItem),
    meta: raw.meta,
  };
}
