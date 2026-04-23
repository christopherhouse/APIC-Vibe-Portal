/**
 * MCP Inspector API client functions.
 *
 * Calls the BFF proxy endpoints that relay requests to actual MCP servers
 * registered in the API catalog.
 */

import { apiClient } from '@/lib/api-client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A single property in an MCP tool's JSON input schema. */
export interface McpToolProperty {
  /** JSON Schema type of this property (e.g. 'string', 'number', 'boolean'). */
  type: string;
  /** Human-readable description of this property's purpose. */
  description?: string;
  /** Allowed discrete values; when present, render as a select/dropdown. */
  enum?: string[];
}

/** The JSON Schema for an MCP tool's input parameters. */
export interface McpToolInputSchema {
  type: string;
  properties?: Record<string, McpToolProperty>;
  required?: string[];
  description?: string;
}

/** A tool exposed by an MCP server. */
export interface McpTool {
  name: string;
  description?: string;
  inputSchema?: McpToolInputSchema;
}

/** An argument accepted by an MCP prompt template. */
export interface McpPromptArgument {
  name: string;
  description?: string;
  required?: boolean;
}

/** A prompt template exposed by an MCP server. */
export interface McpPrompt {
  name: string;
  description?: string;
  arguments?: McpPromptArgument[];
}

/** A resource exposed by an MCP server. */
export interface McpResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

/** Aggregated capabilities of an MCP server. */
export interface McpCapabilities {
  serverUrl: string;
  tools: McpTool[];
  prompts: McpPrompt[];
  resources: McpResource[];
}

/** A single content item returned by an MCP tool invocation. */
export interface McpContentItem {
  type: string;
  text?: string;
  data?: unknown;
  mimeType?: string;
}

/** The result of invoking an MCP tool. */
export interface McpInvokeResult {
  content: McpContentItem[];
  isError: boolean;
  durationMs: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

interface McpCapabilitiesEnvelope {
  data: McpCapabilities;
}

interface McpInvokeEnvelope {
  data: McpInvokeResult;
}

/**
 * Fetch the tools, prompts, and resources exposed by an MCP server.
 *
 * The BFF resolves the server URL from the API's deployment entry and proxies
 * the MCP capability listing calls.
 */
export async function fetchMcpCapabilities(apiId: string): Promise<McpCapabilities> {
  const response = await apiClient.get<McpCapabilitiesEnvelope>(
    `/api/mcp/${encodeURIComponent(apiId)}/capabilities`
  );
  return response.data;
}

/**
 * Invoke an MCP tool by name with the supplied arguments.
 */
export async function invokeMcpTool(
  apiId: string,
  toolName: string,
  args: Record<string, unknown>
): Promise<McpInvokeResult> {
  const response = await apiClient.post<McpInvokeEnvelope>(
    `/api/mcp/${encodeURIComponent(apiId)}/invoke`,
    { tool_name: toolName, arguments: args }
  );
  return response.data;
}
