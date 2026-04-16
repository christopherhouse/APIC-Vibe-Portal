/**
 * API catalog data fetching functions.
 *
 * These functions call the BFF `/api/catalog` endpoint and return typed
 * responses matching the shared types package.
 */

import type { ApiCatalogItem, PaginationMeta } from '@apic-vibe-portal/shared';

const BFF_BASE_URL = process.env.NEXT_PUBLIC_BFF_URL ?? 'http://localhost:8000';

/** Parameters accepted by the catalog list endpoint. */
export interface CatalogListParams {
  page?: number;
  pageSize?: number;
  sort?: string;
  direction?: string;
  lifecycle?: string[];
  kind?: string[];
}

/** Shape of the BFF list-APIs response envelope. */
export interface CatalogListResponse {
  data: ApiCatalogItem[];
  meta: PaginationMeta;
}

/**
 * Fetch a paginated, filtered, sorted list of APIs from the BFF.
 *
 * Designed to be called both server-side (initial SSR) and client-side
 * (when filters / sort / page change).
 */
export async function fetchCatalogApis(
  params: CatalogListParams = {},
  init?: RequestInit
): Promise<CatalogListResponse> {
  const url = new URL('/api/catalog', BFF_BASE_URL);

  if (params.page) url.searchParams.set('page', String(params.page));
  if (params.pageSize) url.searchParams.set('pageSize', String(params.pageSize));
  if (params.sort) url.searchParams.set('sort', params.sort);
  if (params.direction) url.searchParams.set('direction', params.direction);
  if (params.lifecycle?.length) {
    // BFF accepts a single lifecycle value; send the first selected
    url.searchParams.set('lifecycle', params.lifecycle[0]);
  }
  if (params.kind?.length) {
    url.searchParams.set('kind', params.kind[0]);
  }

  const res = await fetch(url.toString(), {
    headers: { Accept: 'application/json' },
    ...init,
  });

  if (!res.ok) {
    throw new Error(`Catalog API error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<CatalogListResponse>;
}
