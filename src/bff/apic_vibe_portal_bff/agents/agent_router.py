"""Agent router — dispatches requests to the appropriate registered agent."""

from __future__ import annotations

import logging
from collections.abc import Generator

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes incoming :class:`~apic_vibe_portal_bff.agents.types.AgentRequest` objects
    to the correct registered agent.

    Currently all requests are routed to :attr:`~apic_vibe_portal_bff.agents.types.AgentName.API_DISCOVERY`.
    The routing logic is intentionally centralised here so that intent-based
    routing (e.g. via a classifier LLM call) can be added in a future task
    without touching agent implementations.

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
        # For now all requests are routed to the API Discovery Agent.
        # Future: analyse ``request.message`` with a lightweight classifier
        # to route to specialised agents (security, governance, analytics, …).
        return AgentName.API_DISCOVERY

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, request: AgentRequest) -> AgentResponse:
        """Route *request* and return the agent's response.

        Parameters
        ----------
        request:
            The incoming agent request.

        Raises
        ------
        ValueError
            If no agent is registered for the resolved :class:`AgentName`.
        """
        agent_name = self.route(request)
        agent = self._registry.get(agent_name)
        if agent is None:
            raise ValueError(f"No agent registered for name: {agent_name!r}")
        logger.info("AgentRouter dispatching to agent=%s session=%s", agent_name, request.session_id)
        return agent.run(request)

    def dispatch_stream(self, request: AgentRequest) -> Generator[str]:
        """Route *request* and stream the agent's response.

        Parameters
        ----------
        request:
            The incoming agent request.

        Raises
        ------
        ValueError
            If no agent is registered for the resolved :class:`AgentName`.

        Yields
        ------
        str
            Text chunks from the agent response stream.
        """
        agent_name = self.route(request)
        agent = self._registry.get(agent_name)
        if agent is None:
            raise ValueError(f"No agent registered for name: {agent_name!r}")
        logger.info("AgentRouter streaming from agent=%s session=%s", agent_name, request.session_id)
        yield from agent.stream(request)
