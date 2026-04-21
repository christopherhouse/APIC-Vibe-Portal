/**
 * Metadata completeness API client.
 *
 * Calls the BFF `/api/metadata` endpoints for completeness scoring,
 * recommendations, and organization-wide insights.
 */

import { apiClient } from '@/lib/api-client';

/** Score for a single dimension. */
export interface DimensionScore {
  key: string;
  name: string;
  weight: number;
  score: number;
}

/** Completeness score for a single API. */
export interface CompletenessScoreData {
  apiId: string;
  apiName: string;
  overallScore: number;
  grade: string;
  dimensions: DimensionScore[];
  lastChecked: string;
}

/** A single improvement recommendation. */
export interface Recommendation {
  id: string;
  dimension: string;
  title: string;
  description: string;
  example: string;
  impact: number;
  effort: 'low' | 'medium' | 'high';
  priority: number;
}

/** Recommendations response for a single API. */
export interface RecommendationsData {
  apiId: string;
  apiName: string;
  overallScore: number;
  grade: string;
  recommendations: Recommendation[];
  generatedAt: string;
}

/** Average dimension score. */
export interface DimensionAverage {
  key: string;
  name: string;
  weight: number;
  averageScore: number;
}

/** Organization-wide completeness overview. */
export interface CompletenessOverviewData {
  averageScore: number;
  averageGrade: string;
  totalApis: number;
  distribution: Record<string, number>;
  dimensionAverages: DimensionAverage[];
}

/** Leaderboard entry. */
export interface LeaderboardEntry {
  apiId: string;
  apiName: string;
  score: number;
  grade: string;
}

/** Completeness leaderboard. */
export interface LeaderboardData {
  top: LeaderboardEntry[];
  bottom: LeaderboardEntry[];
}

/** Fetch completeness score for a single API. */
export async function fetchCompletenessScore(apiId: string): Promise<CompletenessScoreData> {
  return apiClient.get<CompletenessScoreData>(`/api/metadata/${encodeURIComponent(apiId)}/score`);
}

/** Fetch recommendations for a single API. */
export async function fetchRecommendations(apiId: string): Promise<RecommendationsData> {
  return apiClient.get<RecommendationsData>(
    `/api/metadata/${encodeURIComponent(apiId)}/recommendations`
  );
}

/** Fetch organization-wide completeness overview. */
export async function fetchCompletenessOverview(): Promise<CompletenessOverviewData> {
  return apiClient.get<CompletenessOverviewData>('/api/metadata/overview');
}

/** Fetch completeness leaderboard. */
export async function fetchCompletenessLeaderboard(): Promise<LeaderboardData> {
  return apiClient.get<LeaderboardData>('/api/metadata/leaderboard');
}
