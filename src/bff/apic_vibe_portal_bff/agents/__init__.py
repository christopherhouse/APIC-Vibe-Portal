"""Agent system for the APIC Vibe Portal BFF.

Provides a multi-agent architecture with:
- :class:`~apic_vibe_portal_bff.agents.types.AgentRequest` /
  :class:`~apic_vibe_portal_bff.agents.types.AgentResponse` — typed request/response models
- :class:`~apic_vibe_portal_bff.agents.base_agent.BaseAgent` — abstract agent interface
- :class:`~apic_vibe_portal_bff.agents.agent_registry.AgentRegistry` — agent registration
- :class:`~apic_vibe_portal_bff.agents.agent_router.AgentRouter` — intent-based routing
- :mod:`~apic_vibe_portal_bff.agents.api_discovery_agent` — API Discovery Agent
"""

from __future__ import annotations

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.agent_router import AgentRouter
from apic_vibe_portal_bff.agents.base_agent import BaseAgent
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse

__all__ = [
    "AgentName",
    "AgentRegistry",
    "AgentRequest",
    "AgentResponse",
    "AgentRouter",
    "BaseAgent",
]
