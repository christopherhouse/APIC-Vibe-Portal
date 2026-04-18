/**
 * API catalog detail data fetching functions.
 *
 * These functions call the BFF `/api/catalog/:apiId` endpoints and return
 * typed responses for the API detail page.
 */

import type { ApiDefinition, ApiVersion, ApiDeployment } from '@apic-vibe-portal/shared';
import { apiClient } from '@/lib/api-client';

/** BFF response envelope for a single API detail. */
export interface ApiDetailEnvelope {
  data: ApiDefinition;
}

/** BFF response envelope for a versions list. */
export interface ApiVersionsEnvelope {
  data: ApiVersion[];
}

/** BFF response envelope for a deployments list. */
export interface ApiDeploymentsEnvelope {
  data: ApiDeployment[];
}

/**
 * Fetch full API details by ID.
 */
export async function fetchApiDetail(apiId: string): Promise<ApiDefinition> {
  const response = await apiClient.get<ApiDetailEnvelope>(
    `/api/catalog/${encodeURIComponent(apiId)}`
  );
  return response.data;
}

/**
 * Fetch versions for a specific API.
 */
export async function fetchApiVersions(apiId: string): Promise<ApiVersion[]> {
  const response = await apiClient.get<ApiVersionsEnvelope>(
    `/api/catalog/${encodeURIComponent(apiId)}/versions`
  );
  return response.data;
}

/** BFF response shape for an API specification document. */
export interface ApiSpecificationData {
  id: string;
  name: string;
  title: string;
  specificationType?: string | null;
  specificationVersion?: string | null;
  content: string | null;
}

/**
 * Fetch the API definition/spec for a specific version.
 * Returns the raw spec content as a string.
 */
export async function fetchApiDefinition(apiId: string, versionId: string): Promise<string | null> {
  const response = await apiClient.get<{ data: ApiSpecificationData }>(
    `/api/catalog/${encodeURIComponent(apiId)}/versions/${encodeURIComponent(versionId)}/definition`
  );
  return response.data.content;
}

/**
 * Fetch deployments for a specific API.
 */
export async function fetchApiDeployments(apiId: string): Promise<ApiDeployment[]> {
  const response = await apiClient.get<ApiDeploymentsEnvelope>(
    `/api/catalog/${encodeURIComponent(apiId)}/deployments`
  );
  return response.data;
}
