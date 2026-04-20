"""Cross-agent conversation context management.

Maintains conversation history and context across agent switches, ensuring
smooth hand-offs and continuity in multi-agent conversations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from apic_vibe_portal_bff.agents.types import AgentName

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""

    timestamp: datetime
    agent_name: AgentName
    user_message: str
    agent_response: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "user_message": self.user_message,
            "agent_response": self.agent_response,
            "metadata": self.metadata,
        }


@dataclass
class AgentHandoff:
    """Record of an agent hand-off event."""

    timestamp: datetime
    from_agent: AgentName
    to_agent: AgentName
    reason: str
    context_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "reason": self.reason,
            "context_summary": self.context_summary,
        }


class ConversationContext:
    """Manages context for a single conversation session.

    Tracks conversation history, agent switches, referenced APIs, and active
    filters. Provides context window management to stay within token limits.

    Parameters
    ----------
    session_id:
        Unique identifier for this conversation session.
    max_turns:
        Maximum number of conversation turns to keep in active context.
        Older turns are summarized to save memory and tokens.
    """

    def __init__(self, session_id: str, max_turns: int = 10) -> None:
        self.session_id = session_id
        self.max_turns = max_turns
        self.turns: list[ConversationTurn] = []
        self.handoffs: list[AgentHandoff] = []
        self.current_agent: AgentName = AgentName.API_DISCOVERY
        self.referenced_apis: set[str] = set()
        self.active_filters: dict[str, Any] = {}
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def add_turn(
        self,
        agent_name: AgentName,
        user_message: str,
        agent_response: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a conversation turn to the context.

        Parameters
        ----------
        agent_name:
            Name of the agent that handled this turn.
        user_message:
            User's message.
        agent_response:
            Agent's response.
        metadata:
            Optional metadata about the turn (e.g., tool calls, citations).
        """
        turn = ConversationTurn(
            timestamp=datetime.now(UTC),
            agent_name=agent_name,
            user_message=user_message,
            agent_response=agent_response,
            metadata=metadata or {},
        )
        self.turns.append(turn)
        self.current_agent = agent_name
        self.updated_at = datetime.now(UTC)

        # Extract referenced APIs from metadata if available
        if metadata and "citations" in metadata:
            for citation in metadata.get("citations", []):
                if "api_id" in citation:
                    self.referenced_apis.add(citation["api_id"])

        # Trim old turns if we exceed max_turns
        if len(self.turns) > self.max_turns:
            self._trim_old_turns()

    def record_handoff(
        self,
        from_agent: AgentName,
        to_agent: AgentName,
        reason: str,
        context_summary: str | None = None,
    ) -> None:
        """Record an agent hand-off event.

        Parameters
        ----------
        from_agent:
            Agent that is handing off the conversation.
        to_agent:
            Agent receiving the conversation.
        reason:
            Reason for the hand-off.
        context_summary:
            Optional summary of conversation context for the new agent.
        """
        handoff = AgentHandoff(
            timestamp=datetime.now(UTC),
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            context_summary=context_summary,
        )
        self.handoffs.append(handoff)
        self.current_agent = to_agent
        self.updated_at = datetime.now(UTC)
        logger.info(
            "Agent handoff recorded: %s -> %s (reason: %s)",
            from_agent,
            to_agent,
            reason,
        )

    def get_recent_context(self, num_turns: int = 5) -> list[ConversationTurn]:
        """Get the most recent conversation turns.

        Parameters
        ----------
        num_turns:
            Number of recent turns to retrieve.

        Returns
        -------
        list[ConversationTurn]
            Most recent turns, up to ``num_turns``.
        """
        return self.turns[-num_turns:]

    def get_context_summary(self) -> str:
        """Generate a text summary of the conversation context.

        Returns
        -------
        str
            Human-readable summary of the conversation so far.
        """
        summary_parts = [
            f"Conversation session {self.session_id}",
            f"Started at: {self.created_at.isoformat()}",
            f"Current agent: {self.current_agent}",
            f"Total turns: {len(self.turns)}",
        ]

        if not self.turns:
            summary_parts.append("No conversation history yet.")

        if self.handoffs:
            summary_parts.append(f"Agent switches: {len(self.handoffs)}")

        if self.referenced_apis:
            summary_parts.append(f"Referenced APIs: {len(self.referenced_apis)}")

        # Add recent turns
        recent = self.get_recent_context(num_turns=3)
        if recent and self.turns:
            summary_parts.append("\nRecent conversation:")
            for turn in recent:
                summary_parts.append(f"  User: {turn.user_message[:100]}...")
                summary_parts.append(f"  {turn.agent_name}: {turn.agent_response[:100]}...")

        return "\n".join(summary_parts)

    def set_filter(self, key: str, value: Any) -> None:
        """Set an active filter that applies to subsequent queries.

        Parameters
        ----------
        key:
            Filter key (e.g., "api_type", "owner").
        value:
            Filter value.
        """
        self.active_filters[key] = value
        self.updated_at = datetime.now(UTC)

    def clear_filters(self) -> None:
        """Clear all active filters."""
        self.active_filters.clear()
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization.

        Returns
        -------
        dict[str, Any]
            Serializable dictionary representation of the context.
        """
        return {
            "session_id": self.session_id,
            "max_turns": self.max_turns,
            "current_agent": self.current_agent,
            "turns": [t.to_dict() for t in self.turns],
            "handoffs": [h.to_dict() for h in self.handoffs],
            "referenced_apis": list(self.referenced_apis),
            "active_filters": self.active_filters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def _trim_old_turns(self) -> None:
        """Remove oldest turns to stay within max_turns limit."""
        excess = len(self.turns) - self.max_turns
        if excess > 0:
            logger.debug(
                "Trimming %d old turns from session %s (max_turns=%d)",
                excess,
                self.session_id,
                self.max_turns,
            )
            self.turns = self.turns[excess:]


class ContextManager:
    """Manages conversation contexts across multiple sessions.

    Parameters
    ----------
    max_turns_per_session:
        Maximum turns to keep per session before trimming.
    """

    def __init__(self, max_turns_per_session: int = 10) -> None:
        self.max_turns = max_turns_per_session
        self._contexts: dict[str, ConversationContext] = {}

    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get existing context or create a new one for the session.

        Parameters
        ----------
        session_id:
            Session identifier.

        Returns
        -------
        ConversationContext
            Context for this session.
        """
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(
                session_id=session_id,
                max_turns=self.max_turns,
            )
        return self._contexts[session_id]

    def clear_context(self, session_id: str) -> None:
        """Clear context for a session.

        Parameters
        ----------
        session_id:
            Session to clear.
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info("Cleared context for session %s", session_id)

    def clear_all(self) -> None:
        """Clear all contexts (primarily for testing)."""
        self._contexts.clear()

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs.

        Returns
        -------
        list[str]
            List of session IDs with active contexts.
        """
        return list(self._contexts.keys())
