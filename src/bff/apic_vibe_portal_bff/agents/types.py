"""Agent-related type definitions for the APIC Vibe Portal agent system."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from apic_vibe_portal_bff.models.chat import Citation


class AgentName(StrEnum):
    """Known agent identifiers registered in the :class:`AgentRegistry`."""

    API_DISCOVERY = "api_discovery"


class AgentRequest(BaseModel):
    """A request dispatched through the agent router."""

    message: str = Field(..., description="User message to the agent")
    session_id: str | None = Field(default=None, description="Session ID for conversation continuity")
    accessible_api_ids: list[str] | None = Field(
        default=None,
        description=(
            "Accessible API IDs for security trimming. "
            "``None`` means no filtering (admin bypass). "
            "An empty list means the user has no accessible APIs."
        ),
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional request metadata")


class AgentResponse(BaseModel):
    """A response produced by an agent."""

    agent_name: AgentName = Field(..., description="Name of the agent that produced this response")
    content: str = Field(..., description="Agent response text")
    session_id: str = Field(..., description="Session identifier")
    citations: list[Citation] | None = Field(default=None, description="Citations to APIs in the catalog")
    tool_calls: list[str] = Field(default_factory=list, description="Names of tools called during processing")
