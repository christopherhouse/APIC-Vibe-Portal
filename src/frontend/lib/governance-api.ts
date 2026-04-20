/**
 * Governance dashboard API client.
 *
 * Calls the BFF `/api/governance` endpoints for governance metrics, scores,
 * and compliance data.
 */

import { apiClient } from '@/lib/api-client';

/** Overall governance summary with KPIs. */
export interface GovernanceSummary {
  overallScore: number;
  compliantCount: number;
  totalCount: number;
  criticalIssues: number;
  improvement: number;
}

/** API governance score with category. */
export interface ApiGovernanceScore {
  apiId: string;
  apiName: string;
  score: number;
  category: 'Excellent' | 'Good' | 'Needs Improvement' | 'Poor';
  criticalFailures: number;
  lastChecked: string;
}

/** Governance rule definition. */
export interface GovernanceRule {
  ruleId: string;
  name: string;
  description: string;
  severity: 'critical' | 'warning' | 'info';
  remediation: string;
}

/** Rule evaluation finding for a single API. */
export interface RuleFinding {
  ruleId: string;
  ruleName: string;
  severity: 'critical' | 'warning' | 'info';
  passed: boolean;
  message: string;
  remediation: string;
}

/** API compliance report. */
export interface ApiCompliance {
  apiId: string;
  apiName: string;
  score: number;
  category: 'Excellent' | 'Good' | 'Needs Improvement' | 'Poor';
  criticalFailures: number;
  findings: RuleFinding[];
  lastChecked: string;
}

/** Governance trend data point. */
export interface TrendDataPoint {
  date: string;
  averageScore: number;
}

/** Governance trends over time. */
export interface GovernanceTrends {
  dataPoints: TrendDataPoint[];
  summary: {
    startScore: number;
    endScore: number;
    change: number;
  };
}

/** Score distribution across categories. */
export interface ScoreDistribution {
  excellent: number;
  good: number;
  needsImprovement: number;
  poor: number;
}

/** Rule compliance rate. */
export interface RuleCompliance {
  ruleId: string;
  ruleName: string;
  severity: 'critical' | 'warning' | 'info';
  passCount: number;
  failCount: number;
  complianceRate: number;
}

/** Fetch overall governance summary. */
export async function fetchGovernanceSummary(): Promise<GovernanceSummary> {
  return apiClient.get<GovernanceSummary>('/api/governance/summary');
}

/** Fetch governance scores for all APIs. */
export async function fetchGovernanceScores(): Promise<ApiGovernanceScore[]> {
  return apiClient.get<ApiGovernanceScore[]>('/api/governance/scores');
}

/** Fetch available governance rules. */
export async function fetchGovernanceRules(): Promise<GovernanceRule[]> {
  return apiClient.get<GovernanceRule[]>('/api/governance/rules');
}

/** Fetch compliance report for a single API. */
export async function fetchApiCompliance(apiId: string): Promise<ApiCompliance> {
  return apiClient.get<ApiCompliance>(`/api/governance/apis/${encodeURIComponent(apiId)}/compliance`);
}

/** Fetch governance score trends over time. */
export async function fetchGovernanceTrends(days: number = 30): Promise<GovernanceTrends> {
  return apiClient.get<GovernanceTrends>(`/api/governance/trends?days=${days}`);
}

/** Fetch score distribution across categories. */
export async function fetchScoreDistribution(): Promise<ScoreDistribution> {
  return apiClient.get<ScoreDistribution>('/api/governance/distribution');
}

/** Fetch compliance rates per governance rule. */
export async function fetchRuleCompliance(): Promise<RuleCompliance[]> {
  return apiClient.get<RuleCompliance[]>('/api/governance/rule-compliance');
}
