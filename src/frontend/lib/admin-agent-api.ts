/**
 * API client for agent management endpoints.
 *
 * All endpoints require the Portal.Admin role.
 */

const API_BASE = process.env.NEXT_PUBLIC_BFF_API_URL || '/api';

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
 * Fetch authorization token for API requests.
 */
async function getAuthToken(): Promise<string> {
  // In production, this would get the token from MSAL
  // For now, we'll assume the token is available via a module
  const { getAccessToken } = await import('@/lib/auth/use-auth');
  const token = await getAccessToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  return token;
}

/**
 * List all registered agents.
 */
export async function fetchAgents(): Promise<AgentInfo[]> {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE}/admin/agents`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to fetch agents' }));
    throw new Error(error.message || 'Failed to fetch agents');
  }

  return response.json();
}

/**
 * Get detailed information for a specific agent.
 */
export async function fetchAgentDetail(agentId: string): Promise<AgentDetail> {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE}/admin/agents/${encodeURIComponent(agentId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to fetch agent details' }));
    throw new Error(error.message || 'Failed to fetch agent details');
  }

  return response.json();
}

/**
 * Get usage statistics for a specific agent.
 */
export async function fetchAgentStats(agentId: string): Promise<AgentStats> {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE}/admin/agents/${encodeURIComponent(agentId)}/stats`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ message: 'Failed to fetch agent statistics' }));
    throw new Error(error.message || 'Failed to fetch agent statistics');
  }

  return response.json();
}

/**
 * Test an agent with a sample query.
 */
export async function testAgent(
  agentId: string,
  request: AgentTestRequest
): Promise<AgentTestResponse> {
  const token = await getAuthToken();
  const response = await fetch(`${API_BASE}/admin/agents/${encodeURIComponent(agentId)}/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to test agent' }));
    throw new Error(error.message || 'Failed to test agent');
  }

  return response.json();
}
