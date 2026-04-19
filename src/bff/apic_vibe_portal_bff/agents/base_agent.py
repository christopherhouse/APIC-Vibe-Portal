"""Abstract base class for all APIC Portal agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator

from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse


class BaseAgent(ABC):
    """Abstract interface that every agent in the portal must implement.

    Concrete agents (e.g. :class:`~apic_vibe_portal_bff.agents.api_discovery_agent.definition.ApiDiscoveryAgent`)
    extend this class and provide their own tool definitions and prompts.
    """

    @property
    @abstractmethod
    def name(self) -> AgentName:
        """Unique identifier used to register and look up the agent."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable summary of the agent's capabilities."""
        ...

    @abstractmethod
    def run(self, request: AgentRequest) -> AgentResponse:
        """Process a request and return a complete response.

        Parameters
        ----------
        request:
            The incoming agent request, including the user message, session ID,
            and any security-trimming metadata.

        Returns
        -------
        :class:`~apic_vibe_portal_bff.agents.types.AgentResponse`
        """
        ...

    @abstractmethod
    def stream(self, request: AgentRequest) -> Generator[str]:
        """Stream a response token by token.

        Parameters
        ----------
        request:
            The incoming agent request.

        Yields
        ------
        str
            Individual text chunks that together form the full response.
        """
        ...
