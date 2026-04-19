/**
 * Admin API client for managing API access policies.
 *
 * Calls the BFF `/api/admin/access-policies` endpoints which require the
 * `Portal.Admin` role.
 */

import { apiClient } from '@/lib/api-client';

/** An API access policy as returned by the BFF. */
export interface AccessPolicy {
  apiName: string;
  apiId: string;
  allowedGroups: string[];
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Request body for creating or replacing an access policy. */
export interface AccessPolicyRequest {
  allowedGroups: string[];
  isPublic: boolean;
  apiId?: string;
}

/** Fetch all configured access policies. */
export async function fetchAccessPolicies(): Promise<AccessPolicy[]> {
  return apiClient.get<AccessPolicy[]>('/api/admin/access-policies');
}

/** Fetch the access policy for a specific API. */
export async function fetchAccessPolicy(apiName: string): Promise<AccessPolicy> {
  return apiClient.get<AccessPolicy>(`/api/admin/access-policies/${encodeURIComponent(apiName)}`);
}

/** Create or replace the access policy for an API. */
export async function upsertAccessPolicy(
  apiName: string,
  policy: AccessPolicyRequest
): Promise<AccessPolicy> {
  return apiClient.put<AccessPolicy>(
    `/api/admin/access-policies/${encodeURIComponent(apiName)}`,
    policy
  );
}

/** Delete the access policy for an API (makes the API public again). */
export async function deleteAccessPolicy(apiName: string): Promise<void> {
  return apiClient.delete<void>(
    `/api/admin/access-policies/${encodeURIComponent(apiName)}`
  );
}

/** Force immediate refresh of the in-memory policy cache on the BFF. */
export async function invalidatePolicyCache(): Promise<void> {
  return apiClient.post<void>('/api/admin/access-policies/cache/invalidate');
}
