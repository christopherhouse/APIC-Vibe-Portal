import { ApiDefinition } from '../models/api-definition.js';
import { GovernanceStatus } from '../enums/governance-status.js';

/**
 * Governance information included in the API detail response.
 */
export interface GovernanceInfo {
  status: GovernanceStatus;
  lastEvaluatedAt?: string;
  ruleResults?: GovernanceRuleResult[];
}

/**
 * Result of a single governance rule evaluation.
 */
export interface GovernanceRuleResult {
  ruleId: string;
  ruleName: string;
  status: GovernanceStatus;
  message?: string;
}

/**
 * Response DTO for the API detail endpoint.
 */
export interface ApiDetailResponse {
  api: ApiDefinition;
  governance?: GovernanceInfo;
}
