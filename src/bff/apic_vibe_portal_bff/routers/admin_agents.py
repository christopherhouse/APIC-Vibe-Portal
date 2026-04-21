"""Admin endpoints for agent management.

These endpoints allow portal administrators to view and manage agents,
including agent configurations, statistics, and testing.

All endpoints require the ``Portal.Admin`` role.

Endpoints
---------
GET    /api/admin/agents                — List all registered agents
GET    /api/admin/agents/{agent_id}     — Get agent details
GET    /api/admin/agents/{agent_id}/stats — Get agent usage statistics
POST   /api/admin/agents/{agent_id}/test  — Test agent with sample query
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest
from apic_vibe_portal_bff.middleware.rbac import require_role

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AgentInfo(BaseModel):
    """Basic agent information."""

    agent_id: str = Field(..., alias="agentId")
    name: str
    description: str
    status: str = "active"  # active, inactive, error
    registered_at: str = Field(..., alias="registeredAt")

    model_config = {"populate_by_name": True}


class AgentDetail(AgentInfo):
    """Detailed agent information including configuration."""

    configuration: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)


class AgentStats(BaseModel):
    """Agent usage statistics."""

    agent_id: str = Field(..., alias="agentId")
    queries_handled: int = Field(0, alias="queriesHandled")
    avg_response_time_ms: float = Field(0.0, alias="avgResponseTimeMs")
    success_rate: float = Field(100.0, alias="successRate")
    last_used_at: str | None = Field(None, alias="lastUsedAt")

    model_config = {"populate_by_name": True}


class AgentTestRequest(BaseModel):
    """Request to test an agent with a sample query."""

    query: str = Field(..., description="Sample query to test the agent with")
    session_id: str | None = Field(None, alias="sessionId", description="Optional session ID for context")

    model_config = {"populate_by_name": True}


class AgentTestResponse(BaseModel):
    """Response from agent test."""

    agent_id: str = Field(..., alias="agentId")
    query: str
    response: str
    response_time_ms: float = Field(..., alias="responseTimeMs")
    success: bool
    error: str | None = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


def _get_agent_registry() -> AgentRegistry:
    """Get the global agent registry.

    In a production system, this would be injected from application state.
    For now, we'll create a simple singleton pattern.
    """
    # This is a placeholder - in production, the registry would be stored
    # in FastAPI app.state and injected via dependency
    from apic_vibe_portal_bff.agents.api_discovery_agent import ApiDiscoveryAgent
    from apic_vibe_portal_bff.agents.governance_agent import GovernanceAgent

    registry = AgentRegistry()

    # Register agents if not already registered
    # Note: In production, agents would be registered at app startup
    if len(registry) == 0:
        try:
            # These will fail if dependencies aren't available, which is fine for admin endpoints
            discovery_agent = ApiDiscoveryAgent()
            registry.register(discovery_agent)
        except Exception as e:
            logger.warning("Could not register API Discovery Agent: %s", e)

        try:
            governance_agent = GovernanceAgent()
            registry.register(governance_agent)
        except Exception as e:
            logger.warning("Could not register Governance Agent: %s", e)

    return registry


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["admin", "agents"], prefix="/api/admin/agents")

_ADMIN_ROLE = "Portal.Admin"


@router.get(
    "",
    response_model=list[AgentInfo],
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="List all registered agents",
)
def list_agents(
    registry: AgentRegistry = Depends(_get_agent_registry),  # noqa: B008
) -> list[AgentInfo]:
    """Return all registered agents with basic information.

    Returns
    -------
    list[AgentInfo]
        List of registered agents.
    """
    agents = []
    for agent_name in registry.list_names():
        agent = registry.get(agent_name)
        if agent:
            agents.append(
                AgentInfo(
                    agentId=agent.name,
                    name=agent.name.replace("_", " ").title(),
                    description=agent.description,
                    status="active",
                    registeredAt=datetime.now(UTC).isoformat(),
                )
            )
    return agents


@router.get(
    "/{agent_id}",
    response_model=AgentDetail,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Get detailed agent information",
)
def get_agent_detail(
    agent_id: str,
    registry: AgentRegistry = Depends(_get_agent_registry),  # noqa: B008
) -> AgentDetail:
    """Return detailed information about a specific agent.

    Parameters
    ----------
    agent_id:
        Agent identifier (e.g., "api_discovery", "governance").

    Returns
    -------
    AgentDetail
        Detailed agent information.

    Raises
    ------
    HTTPException
        404 if agent not found.
    """
    try:
        agent_name = AgentName(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Unknown agent ID: {agent_id}"},
        ) from None

    agent = registry.get(agent_name)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Agent not registered: {agent_id}"},
        )

    # Extract capabilities from agent (placeholder - could be enhanced)
    capabilities = ["query_processing", "tool_calling"]
    if agent_name == AgentName.API_DISCOVERY:
        capabilities.extend(["api_search", "api_details", "api_comparison"])
    elif agent_name == AgentName.GOVERNANCE:
        capabilities.extend(["compliance_check", "governance_scoring", "remediation_guidance"])

    return AgentDetail(
        agentId=agent.name,
        name=agent.name.replace("_", " ").title(),
        description=agent.description,
        status="active",
        registeredAt=datetime.now(UTC).isoformat(),
        configuration={
            "name": agent.name,
            "description": agent.description,
        },
        capabilities=capabilities,
    )


@router.get(
    "/{agent_id}/stats",
    response_model=AgentStats,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Get agent usage statistics",
)
def get_agent_stats(
    agent_id: str,
    registry: AgentRegistry = Depends(_get_agent_registry),  # noqa: B008
) -> AgentStats:
    """Return usage statistics for a specific agent.

    Parameters
    ----------
    agent_id:
        Agent identifier.

    Returns
    -------
    AgentStats
        Agent usage statistics.

    Raises
    ------
    HTTPException
        404 if agent not found.
    """
    try:
        agent_name = AgentName(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Unknown agent ID: {agent_id}"},
        ) from None

    agent = registry.get(agent_name)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Agent not registered: {agent_id}"},
        )

    # Placeholder statistics - in production, these would come from telemetry
    return AgentStats(
        agentId=agent_id,
        queriesHandled=0,
        avgResponseTimeMs=0.0,
        successRate=100.0,
        lastUsedAt=None,
    )


@router.post(
    "/{agent_id}/test",
    response_model=AgentTestResponse,
    dependencies=[Depends(require_role(_ADMIN_ROLE))],
    summary="Test agent with a sample query",
)
async def test_agent(
    agent_id: str,
    body: AgentTestRequest,
    registry: AgentRegistry = Depends(_get_agent_registry),  # noqa: B008
) -> AgentTestResponse:
    """Test an agent with a sample query.

    Parameters
    ----------
    agent_id:
        Agent identifier.
    body:
        Test request with query.

    Returns
    -------
    AgentTestResponse
        Test results.

    Raises
    ------
    HTTPException
        404 if agent not found, 500 if test fails.
    """
    try:
        agent_name = AgentName(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Unknown agent ID: {agent_id}"},
        ) from None

    agent = registry.get(agent_name)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Agent not registered: {agent_id}"},
        )

    # Create test request
    request = AgentRequest(
        message=body.query,
        session_id=body.session_id or f"test-{agent_id}",
        accessible_api_ids=None,  # Admin bypass
    )

    # Execute test
    start_time = datetime.now(UTC)
    try:
        response = await agent.run(request)
        end_time = datetime.now(UTC)
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        return AgentTestResponse(
            agentId=agent_id,
            query=body.query,
            response=response.content,
            responseTimeMs=response_time_ms,
            success=True,
        )
    except Exception:
        end_time = datetime.now(UTC)
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        logger.exception("Agent test failed: agent_id=%s", agent_id)
        return AgentTestResponse(
            agentId=agent_id,
            query=body.query,
            response="",
            responseTimeMs=response_time_ms,
            success=False,
            error="Agent test failed. Check server logs for details.",
        )
