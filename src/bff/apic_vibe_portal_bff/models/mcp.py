"""Pydantic models for the MCP Inspector feature.

These models represent the data exchanged between the frontend MCP Inspector
UI and the BFF proxy routes that communicate with actual MCP servers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apic_vibe_portal_bff.models.api_center import CamelModel

# ---------------------------------------------------------------------------
# MCP capability models (returned by GET /api/mcp/{api_id}/capabilities)
# ---------------------------------------------------------------------------


class McpToolInputSchema(CamelModel):
    """JSON Schema describing the input parameters for an MCP tool."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    description: str | None = None


class McpTool(CamelModel):
    """A tool exposed by an MCP server."""

    name: str
    description: str | None = None
    input_schema: McpToolInputSchema = Field(default_factory=McpToolInputSchema)


class McpPromptArgument(CamelModel):
    """An argument accepted by an MCP prompt."""

    name: str
    description: str | None = None
    required: bool = False


class McpPrompt(CamelModel):
    """A prompt template exposed by an MCP server."""

    name: str
    description: str | None = None
    arguments: list[McpPromptArgument] = Field(default_factory=list)


class McpResource(CamelModel):
    """A resource exposed by an MCP server."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str | None = None


class McpCapabilities(CamelModel):
    """Aggregated capabilities of an MCP server."""

    server_url: str
    tools: list[McpTool] = Field(default_factory=list)
    prompts: list[McpPrompt] = Field(default_factory=list)
    resources: list[McpResource] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# MCP invocation models (used by POST /api/mcp/{api_id}/invoke)
# ---------------------------------------------------------------------------


class McpInvokeRequest(BaseModel):
    """Request body for invoking an MCP tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class McpContentItem(CamelModel):
    """A single content item in an MCP tool invocation result."""

    type: str
    text: str | None = None
    data: Any | None = None
    mime_type: str | None = None


class McpInvokeResult(CamelModel):
    """The result of invoking an MCP tool."""

    content: list[McpContentItem] = Field(default_factory=list)
    is_error: bool = False
    duration_ms: float = 0.0
