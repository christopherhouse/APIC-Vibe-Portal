/**
 * API comparison data fetching functions.
 *
 * These functions call the BFF `/api/compare` endpoints and return typed
 * responses for the comparison feature.
 */

import { apiClient } from '@/lib/api-client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CompareAspect =
  | 'metadata'
  | 'versions'
  | 'endpoints'
  | 'governance'
  | 'deployments'
  | 'specifications';

export interface CompareRequest {
  /** 2–5 API IDs to compare. */
  apiIds: string[];
  /** Optional subset of aspects to include. Defaults to all aspects. */
  aspects?: CompareAspect[];
}

export interface CompareApiSummary {
  id: string;
  name: string;
  title: string;
  description: string;
  kind: string;
  lifecycleStage: string;
}

export interface AspectValue {
  value: string | null;
  display: string | null;
  /** True when this value is the 'best' in its row (for visual highlighting). */
  isBest: boolean;
}

export interface AspectComparison {
  aspect: string;
  label: string;
  /** One entry per API, in the same order as CompareResponse.apis. */
  values: AspectValue[];
  allEqual: boolean;
}

export interface CompareResponse {
  apis: CompareApiSummary[];
  aspects: AspectComparison[];
  /** Fraction of aspects identical across all APIs (0–1). */
  similarityScore: number;
  /** Only populated by the ai-analysis endpoint. */
  aiAnalysis: string | null;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Compare 2–5 APIs and return structured aspect comparison data.
 * Does not include AI narrative analysis.
 */
export async function compareApis(request: CompareRequest): Promise<CompareResponse> {
  return apiClient.post<CompareResponse>('/api/compare', request);
}

/**
 * Compare 2–5 APIs and include an AI-generated narrative analysis.
 */
export async function compareApisWithAi(request: CompareRequest): Promise<CompareResponse> {
  return apiClient.post<CompareResponse>('/api/compare/ai-analysis', request);
}
