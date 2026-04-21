/**
 * Analytics dashboard API client.
 *
 * Calls the BFF `/api/analytics` endpoints for analytics summary, trends,
 * popular APIs, and user activity data.
 */

import { apiClient } from '@/lib/api-client';

/** Predefined time range options. */
export type TimeRange = '7d' | '30d' | '90d' | '1y';

/** Analytics KPI summary. */
export interface AnalyticsSummary {
  totalUsers: number;
  totalPageViews: number;
  totalSearchQueries: number;
  totalChatInteractions: number;
  avgSessionDurationSeconds: number;
  usersTrend: number;
  pageViewsTrend: number;
  searchQueriesTrend: number;
  chatInteractionsTrend: number;
}

/** Usage trend data point (daily). */
export interface UsageTrendPoint {
  date: string;
  activeUsers: number;
  pageViews: number;
  searches: number;
  chatInteractions: number;
}

/** Usage trend response. */
export interface UsageTrends {
  dataPoints: UsageTrendPoint[];
  range: TimeRange;
}

/** Popular API entry. */
export interface PopularApi {
  apiId: string;
  apiName: string;
  viewCount: number;
  downloadCount: number;
  chatMentionCount: number;
}

/** Search trend data. */
export interface SearchTrends {
  dailyVolume: Array<{ date: string; queryCount: number; zeroResultCount: number }>;
  topQueries: Array<{
    queryHash: string;
    displayTerm: string;
    count: number;
    avgResultCount: number;
  }>;
  zeroResultQueries: Array<{ displayTerm: string; count: number }>;
  clickThroughRate: number;
  avgResultsPerSearch: number;
  searchModeDistribution: { keyword: number; semantic: number; hybrid: number };
}

/** User activity data. */
export interface UserActivity {
  dailyActiveUsers: Array<{ date: string; count: number }>;
  weeklyActiveUsers: Array<{ week: string; count: number }>;
  avgSessionDurationSeconds: number;
  avgPagesPerSession: number;
  returningUserRate: number;
  featureAdoption: {
    catalog: number;
    search: number;
    chat: number;
    compare: number;
    governance: number;
  };
}

/** Fetch analytics summary KPIs. */
export async function fetchAnalyticsSummary(range: TimeRange = '30d'): Promise<AnalyticsSummary> {
  return apiClient.get<AnalyticsSummary>(`/api/analytics/summary?time_range=${range}`);
}

/** Fetch usage trends over time. */
export async function fetchUsageTrends(range: TimeRange = '30d'): Promise<UsageTrends> {
  return apiClient.get<UsageTrends>(`/api/analytics/usage-trends?time_range=${range}`);
}

/** Fetch most popular APIs. */
export async function fetchPopularApis(
  range: TimeRange = '30d',
  limit = 10
): Promise<PopularApi[]> {
  return apiClient.get<PopularApi[]>(
    `/api/analytics/popular-apis?time_range=${range}&limit=${limit}`
  );
}

/** Fetch search analytics trends. */
export async function fetchSearchTrends(range: TimeRange = '30d'): Promise<SearchTrends> {
  return apiClient.get<SearchTrends>(`/api/analytics/search-trends?time_range=${range}`);
}

/** Fetch user activity data. */
export async function fetchUserActivity(range: TimeRange = '30d'): Promise<UserActivity> {
  return apiClient.get<UserActivity>(`/api/analytics/user-activity?time_range=${range}`);
}
