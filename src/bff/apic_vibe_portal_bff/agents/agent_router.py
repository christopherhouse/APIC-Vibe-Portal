"""Agent router — dispatches requests to the appropriate registered agent."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.base_agent import BaseAgent
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Governance intent keywords
# ---------------------------------------------------------------------------

# Lower-cased keywords that indicate a governance-related user intent.
# Matching is performed on the full lower-cased user message.
_GOVERNANCE_KEYWORDS: frozenset[str] = frozenset(
    {
        "governance",
        "compliance",
        "compliant",
        "non-compliant",
        "noncompliant",
        "non compliant",
        "governance score",
        "governance report",
        "governance status",
        "governance check",
        "governance issue",
        "governance issues",
        "remediat",
        "sunset date",
        "metadata completeness",
        "api standards",
        "api policy",
        "api policies",
        "policy violation",
        "policy check",
        "rule violation",
        "failing rule",
        "failing rules",
        "passes governance",
        "fails governance",
        "governance rule",
        "governance rules",
    }
)


def _is_governance_intent(message: str) -> bool:
    """Return ``True`` if *message* appears to be a governance-related query.

    Uses a keyword-based heuristic so that simple discovery queries are not
    accidentally routed to the Governance Agent.  The check is intentionally
    broad to avoid missing governance queries; the Governance Agent itself will
    handle any ambiguous messages gracefully.
    """
    lower = message.lower()
    return any(kw in lower for kw in _GOVERNANCE_KEYWORDS)


class AgentRouter:
    """Routes incoming :class:`~apic_vibe_portal_bff.agents.types.AgentRequest` objects
    to the correct registered agent.

    Routing strategy:

    1. If the user message contains governance-related keywords, route to the
       :attr:`~apic_vibe_portal_bff.agents.types.AgentName.GOVERNANCE` agent.
    2. All other requests are routed to the
       :attr:`~apic_vibe_portal_bff.agents.types.AgentName.API_DISCOVERY` agent.

    Ambiguous queries default to the Discovery Agent.

    Parameters
    ----------
    registry:
        :class:`~apic_vibe_portal_bff.agents.agent_registry.AgentRegistry` containing
        the registered agent instances.
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, request: AgentRequest) -> AgentName:
        """Determine which agent should handle *request*.

        Parameters
        ----------
        request:
            The incoming agent request.

        Returns
        -------
        :class:`AgentName`
            The name of the agent that should handle the request.
        """
        if _is_governance_intent(request.message):
            return AgentName.GOVERNANCE
        return AgentName.API_DISCOVERY

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_agent_with_fallback(self, agent_name: AgentName) -> tuple[AgentName, BaseAgent | None]:
        """Resolve an agent by name, falling back to API_DISCOVERY if absent.

        Parameters
        ----------
        agent_name:
            The preferred agent name from :meth:`route`.

        Returns
        -------
        tuple[AgentName, BaseAgent | None]
            The effective agent name and instance (``None`` if both the
            preferred and fallback agents are unregistered).
        """
        agent = self._registry.get(agent_name)
        if agent is None and agent_name != AgentName.API_DISCOVERY:
            logger.warning(
                "AgentRouter: no agent registered for %r; falling back to API_DISCOVERY",
                agent_name,
            )
            agent_name = AgentName.API_DISCOVERY
            agent = self._registry.get(agent_name)
        return agent_name, agent

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: AgentRequest) -> AgentResponse:
        """Route *request* and return the agent's response.

        If the resolved agent is not registered (e.g. the Governance Agent is not
        wired up yet), the router transparently falls back to
        :attr:`~AgentName.API_DISCOVERY` before raising so that chat remains
        available even when optional agents are absent.

        Parameters
        ----------
        request:
            The incoming agent request.

        Raises
        ------
        ValueError
            If no agent is registered for the resolved :class:`AgentName` **and**
            the fallback agent is also absent.
        """
        agent_name, agent = self._resolve_agent_with_fallback(self.route(request))
        if agent is None:
            raise ValueError(f"No agent registered for name: {agent_name!r}")
        logger.info("AgentRouter dispatching to agent=%s session=%s", agent_name, request.session_id)
        return await agent.run(request)

    async def dispatch_stream(self, request: AgentRequest) -> AsyncGenerator[str]:
        """Route *request* and stream the agent's response.

        Applies the same fallback logic as :meth:`dispatch` via
        :meth:`_resolve_agent_with_fallback`: if the resolved agent is not
        registered, falls back to the Discovery Agent before raising.

        Parameters
        ----------
        request:
            The incoming agent request.

        Raises
        ------
        ValueError
            If no agent is registered for the resolved :class:`AgentName` **and**
            the fallback agent is also absent.

        Yields
        ------
        str
            Text chunks from the agent response stream.
        """
        agent_name, agent = self._resolve_agent_with_fallback(self.route(request))
        if agent is None:
            raise ValueError(f"No agent registered for name: {agent_name!r}")
        logger.info("AgentRouter streaming from agent=%s session=%s", agent_name, request.session_id)
        async for chunk in agent.stream(request):
            yield chunk
