"""Tests for the conversation context manager."""

from datetime import UTC, datetime

import pytest

from apic_vibe_portal_bff.agents.context_manager import (
    AgentHandoff,
    ContextManager,
    ConversationContext,
    ConversationTurn,
)
from apic_vibe_portal_bff.agents.types import AgentName


class TestConversationTurn:
    """Tests for ConversationTurn."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime.now(UTC)
        turn = ConversationTurn(
            timestamp=timestamp,
            agent_name=AgentName.API_DISCOVERY,
            user_message="Test message",
            agent_response="Test response",
            metadata={"key": "value"},
        )

        data = turn.to_dict()
        assert data["timestamp"] == timestamp.isoformat()
        assert data["agent_name"] == AgentName.API_DISCOVERY
        assert data["user_message"] == "Test message"
        assert data["agent_response"] == "Test response"
        assert data["metadata"]["key"] == "value"


class TestAgentHandoff:
    """Tests for AgentHandoff."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime.now(UTC)
        handoff = AgentHandoff(
            timestamp=timestamp,
            from_agent=AgentName.API_DISCOVERY,
            to_agent=AgentName.GOVERNANCE,
            reason="Test handoff",
            context_summary="Test summary",
        )

        data = handoff.to_dict()
        assert data["timestamp"] == timestamp.isoformat()
        assert data["from_agent"] == AgentName.API_DISCOVERY
        assert data["to_agent"] == AgentName.GOVERNANCE
        assert data["reason"] == "Test handoff"
        assert data["context_summary"] == "Test summary"


class TestConversationContext:
    """Tests for ConversationContext."""

    @pytest.fixture
    def context(self):
        """Create a ConversationContext instance."""
        return ConversationContext(session_id="test-session", max_turns=5)

    def test_init(self, context):
        """Test ConversationContext initialization."""
        assert context.session_id == "test-session"
        assert context.max_turns == 5
        assert len(context.turns) == 0
        assert len(context.handoffs) == 0
        assert context.current_agent == AgentName.API_DISCOVERY
        assert len(context.referenced_apis) == 0
        assert len(context.active_filters) == 0

    def test_add_turn(self, context):
        """Test adding a conversation turn."""
        context.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Find payment APIs",
            agent_response="Here are the payment APIs...",
            metadata={"tool_calls": ["searchApis"]},
        )

        assert len(context.turns) == 1
        assert context.turns[0].agent_name == AgentName.API_DISCOVERY
        assert context.turns[0].user_message == "Find payment APIs"
        assert context.current_agent == AgentName.API_DISCOVERY

    def test_add_turn_extracts_citations(self, context):
        """Test that adding a turn extracts API IDs from citations."""
        context.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Tell me about the API",
            agent_response="Response",
            metadata={
                "citations": [
                    {"api_id": "api-1"},
                    {"api_id": "api-2"},
                ]
            },
        )

        assert "api-1" in context.referenced_apis
        assert "api-2" in context.referenced_apis

    def test_trim_old_turns(self, context):
        """Test that old turns are trimmed when exceeding max_turns."""
        # Add 7 turns (max is 5)
        for i in range(7):
            context.add_turn(
                agent_name=AgentName.API_DISCOVERY,
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
            )

        # Should have trimmed to 5
        assert len(context.turns) == 5
        # First turn should now be message 2 (messages 0 and 1 were trimmed)
        assert context.turns[0].user_message == "Message 2"

    def test_record_handoff(self, context):
        """Test recording an agent handoff."""
        context.record_handoff(
            from_agent=AgentName.API_DISCOVERY,
            to_agent=AgentName.GOVERNANCE,
            reason="User asked about compliance",
            context_summary="Previous conversation summary",
        )

        assert len(context.handoffs) == 1
        assert context.handoffs[0].from_agent == AgentName.API_DISCOVERY
        assert context.handoffs[0].to_agent == AgentName.GOVERNANCE
        assert context.current_agent == AgentName.GOVERNANCE

    def test_get_recent_context(self, context):
        """Test retrieving recent conversation turns."""
        # Add 5 turns
        for i in range(5):
            context.add_turn(
                agent_name=AgentName.API_DISCOVERY,
                user_message=f"Message {i}",
                agent_response=f"Response {i}",
            )

        # Get last 3
        recent = context.get_recent_context(num_turns=3)
        assert len(recent) == 3
        assert recent[0].user_message == "Message 2"
        assert recent[-1].user_message == "Message 4"

    def test_get_recent_context_less_than_requested(self, context):
        """Test retrieving recent context when less than requested exists."""
        context.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Only turn",
            agent_response="Only response",
        )

        recent = context.get_recent_context(num_turns=5)
        assert len(recent) == 1

    def test_get_context_summary_empty(self, context):
        """Test context summary with no turns."""
        summary = context.get_context_summary()
        assert "test-session" in summary
        assert "No conversation history" in summary

    def test_get_context_summary_with_turns(self, context):
        """Test context summary with conversation turns."""
        context.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Find payment APIs",
            agent_response="Here are the results",
        )
        context.add_turn(
            agent_name=AgentName.GOVERNANCE,
            user_message="Check compliance",
            agent_response="Compliance status",
        )

        summary = context.get_context_summary()
        assert "test-session" in summary
        assert "Total turns: 2" in summary
        assert "governance" in summary.lower()

    def test_set_filter(self, context):
        """Test setting active filters."""
        context.set_filter("api_type", "rest")
        assert context.active_filters["api_type"] == "rest"

        context.set_filter("owner", "platform-team")
        assert context.active_filters["owner"] == "platform-team"

    def test_clear_filters(self, context):
        """Test clearing active filters."""
        context.set_filter("api_type", "rest")
        context.set_filter("owner", "platform-team")
        assert len(context.active_filters) == 2

        context.clear_filters()
        assert len(context.active_filters) == 0

    def test_to_dict(self, context):
        """Test converting context to dictionary."""
        context.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Test",
            agent_response="Response",
        )
        context.set_filter("key", "value")

        data = context.to_dict()
        assert data["session_id"] == "test-session"
        assert data["max_turns"] == 5
        assert data["current_agent"] == AgentName.API_DISCOVERY
        assert len(data["turns"]) == 1
        assert data["active_filters"]["key"] == "value"


class TestContextManager:
    """Tests for ContextManager."""

    @pytest.fixture
    def manager(self):
        """Create a ContextManager instance."""
        return ContextManager(max_turns_per_session=10)

    def test_init(self, manager):
        """Test ContextManager initialization."""
        assert manager.max_turns == 10

    def test_get_or_create_context_new(self, manager):
        """Test creating a new context."""
        context = manager.get_or_create_context("session-1")
        assert context.session_id == "session-1"
        assert context.max_turns == 10

    def test_get_or_create_context_existing(self, manager):
        """Test retrieving an existing context."""
        context1 = manager.get_or_create_context("session-1")
        context1.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Test",
            agent_response="Response",
        )

        context2 = manager.get_or_create_context("session-1")
        assert context2 is context1
        assert len(context2.turns) == 1

    def test_multiple_sessions(self, manager):
        """Test managing multiple sessions."""
        context1 = manager.get_or_create_context("session-1")
        context2 = manager.get_or_create_context("session-2")

        context1.add_turn(
            agent_name=AgentName.API_DISCOVERY,
            user_message="Test 1",
            agent_response="Response 1",
        )
        context2.add_turn(
            agent_name=AgentName.GOVERNANCE,
            user_message="Test 2",
            agent_response="Response 2",
        )

        assert len(context1.turns) == 1
        assert len(context2.turns) == 1
        assert context1.turns[0].user_message == "Test 1"
        assert context2.turns[0].user_message == "Test 2"

    def test_clear_context(self, manager):
        """Test clearing a specific session context."""
        manager.get_or_create_context("session-1")
        manager.get_or_create_context("session-2")

        manager.clear_context("session-1")

        # session-1 should be gone
        assert "session-1" not in manager._contexts
        # session-2 should still exist
        assert "session-2" in manager._contexts

    def test_clear_all(self, manager):
        """Test clearing all contexts."""
        manager.get_or_create_context("session-1")
        manager.get_or_create_context("session-2")

        manager.clear_all()

        assert len(manager._contexts) == 0

    def test_get_active_sessions(self, manager):
        """Test retrieving active session IDs."""
        manager.get_or_create_context("session-1")
        manager.get_or_create_context("session-2")
        manager.get_or_create_context("session-3")

        active = manager.get_active_sessions()
        assert len(active) == 3
        assert "session-1" in active
        assert "session-2" in active
        assert "session-3" in active
