"""Agent registry — stores and retrieves registered agent instances."""

from __future__ import annotations

import threading

from apic_vibe_portal_bff.agents.base_agent import BaseAgent
from apic_vibe_portal_bff.agents.types import AgentName


class AgentRegistry:
    """Registry that maps :class:`AgentName` values to :class:`BaseAgent` instances.

    All mutating and read operations are protected by a :class:`threading.Lock`
    so that agents can be registered and looked up from different threads without
    data races.

    Usage::

        registry = AgentRegistry()
        registry.register(my_agent)
        agent = registry.get(AgentName.API_DISCOVERY)
    """

    def __init__(self) -> None:
        self._agents: dict[AgentName, BaseAgent] = {}
        self._lock = threading.Lock()

    def register(self, agent: BaseAgent) -> None:
        """Register an agent.

        If an agent with the same :attr:`~BaseAgent.name` is already registered
        it will be replaced.

        Parameters
        ----------
        agent:
            The agent instance to register.
        """
        with self._lock:
            self._agents[agent.name] = agent

    def get(self, name: AgentName) -> BaseAgent | None:
        """Return the agent registered under *name*, or ``None``.

        Parameters
        ----------
        name:
            The :class:`AgentName` to look up.
        """
        with self._lock:
            return self._agents.get(name)

    def list_names(self) -> list[AgentName]:
        """Return all currently registered agent names."""
        with self._lock:
            return list(self._agents.keys())

    def __len__(self) -> int:
        """Return the number of registered agents."""
        with self._lock:
            return len(self._agents)
