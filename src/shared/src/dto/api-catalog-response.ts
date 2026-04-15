import { ApiDefinition } from '../models/api-definition.js';
import { PaginationMeta } from '../models/pagination.js';

/**
 * Summary of an API for catalog listings.
 */
export interface ApiCatalogItem {
  id: string;
  name: string;
  title: string;
  description: string;
  kind: string;
  lifecycleStage: string;
  versionCount: number;
  deploymentCount: number;
  updatedAt: string;
}

/**
 * Response DTO for the API catalog listing endpoint.
 */
export interface ApiCatalogResponse {
  items: ApiCatalogItem[];
  pagination: PaginationMeta;
}

/**
 * Transform a full ApiDefinition to a catalog item summary.
 */
export function toApiCatalogItem(api: ApiDefinition): ApiCatalogItem {
  return {
    id: api.id,
    name: api.name,
    title: api.title,
    description: api.description,
    kind: api.kind,
    lifecycleStage: api.lifecycleStage,
    versionCount: api.versions.length,
    deploymentCount: api.deployments.length,
    updatedAt: api.updatedAt,
  };
}
