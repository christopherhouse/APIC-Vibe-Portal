/**
 * API client for agent management endpoints.
 *
 * All endpoints require the Portal.Admin role.
 */

import { apiFetch } from './api-client';

const ADMIN_AGENTS_BASE = '/admin/agents';

/**
 * Agent information.
 */
export interface AgentInfo {
  agentId: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'error';
  registeredAt: string;
}

/**
 * Detailed agent information with configuration.
 */
export interface AgentDetail extends AgentInfo {
  configuration: Record<string, unknown>;
  capabilities: string[];
}

/**
 * Agent usage statistics.
 */
export interface AgentStats {
  agentId: string;
  queriesHandled: number;
  avgResponseTimeMs: number;
  successRate: number;
  lastUsedAt: string | null;
}

/**
 * Agent test request.
 */
export interface AgentTestRequest {
  query: string;
  sessionId?: string;
}

/**
 * Agent test response.
 */
export interface AgentTestResponse {
  agentId: string;
  query: string;
  response: string;
  responseTimeMs: number;
  success: boolean;
  error?: string;
}

/**
 * List all registered agents.
 */
export async function fetchAgents(): Promise<AgentInfo[]> {
  return apiFetch<AgentInfo[]>(ADMIN_AGENTS_BASE);
}

/**
 * Get detailed information for a specific agent.
 */
export async function fetchAgentDetail(agentId: string): Promise<AgentDetail> {
  return apiFetch<AgentDetail>(`${ADMIN_AGENTS_BASE}/${encodeURIComponent(agentId)}`);
}

/**
 * Get usage statistics for a specific agent.
 */
export async function fetchAgentStats(agentId: string): Promise<AgentStats> {
  return apiFetch<AgentStats>(`${ADMIN_AGENTS_BASE}/${encodeURIComponent(agentId)}/stats`);
}

/**
 * Test an agent with a sample query.
 */
export async function testAgent(
  agentId: string,
  request: AgentTestRequest
): Promise<AgentTestResponse> {
  return apiFetch<AgentTestResponse>(`${ADMIN_AGENTS_BASE}/${encodeURIComponent(agentId)}/test`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
