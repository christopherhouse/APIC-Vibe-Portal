"""Tests for the agent-powered AI chat service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from apic_vibe_portal_bff.models.chat import ChatResponse
from apic_vibe_portal_bff.services.ai_chat_service import (
    _MAX_CONVERSATION_TURNS,
    _RATE_LIMIT_PER_SESSION,
    _SESSION_EXPIRY_SECONDS,
    AIChatService,
    ChatRateLimitError,
    SessionManager,
    _ChatSession,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_agent_router():
    """Return a mock AgentRouter that produces a deterministic AgentResponse."""
    from apic_vibe_portal_bff.agents.types import AgentName, AgentResponse
    from apic_vibe_portal_bff.models.chat import Citation

    router = MagicMock()
    router.dispatch = AsyncMock(
        return_value=AgentResponse(
            agent_name=AgentName.API_DISCOVERY,
            content="Agent says: here are your APIs.",
            session_id="agent-sess-1",
            citations=[Citation(title="Payments API", url="/api/catalog/payments-api")],
        )
    )
    return router


@pytest.fixture
def service(mock_agent_router):
    """Return an AIChatService with a mock agent router."""
    return AIChatService(
        agent_router=mock_agent_router,
    )


# ---------------------------------------------------------------------------
# Session management tests
# ---------------------------------------------------------------------------


class TestChatSession:
    def test_new_session_not_expired(self):
        session = _ChatSession("test-id")
        assert not session.is_expired()

    def test_session_message_history(self):
        session = _ChatSession("test-id")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        history = session.get_history_messages()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_session_messages_have_stable_ids(self):
        session = _ChatSession("test-id")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        # Each message should have an id and timestamp
        for msg in session.messages:
            assert "id" in msg
            assert "timestamp" in msg
            assert len(msg["id"]) > 0
            assert len(msg["timestamp"]) > 0
        # IDs should be unique
        ids = [m["id"] for m in session.messages]
        assert len(set(ids)) == len(ids)

    def test_session_sliding_window_without_system(self):
        session = _ChatSession("test-id")
        # Add only user messages (no system prompt)
        for i in range(_MAX_CONVERSATION_TURNS * 3):
            session.add_message("user", f"message-{i}")
        # Should trim to max_messages (not pin first message)
        assert len(session.messages) <= _MAX_CONVERSATION_TURNS * 2

    def test_session_sliding_window(self):
        session = _ChatSession("test-id")
        # Add system message first
        session.add_message("system", "System prompt")
        # Add more messages than the window allows
        for i in range(_MAX_CONVERSATION_TURNS * 3):
            session.add_message("user", f"message-{i}")
        # Should have been trimmed
        assert len(session.messages) <= _MAX_CONVERSATION_TURNS * 2 + 1

    def test_session_rate_limit(self):
        session = _ChatSession("test-id")
        # Should allow messages up to the limit
        for _ in range(_RATE_LIMIT_PER_SESSION):
            assert session.check_rate_limit() is True
        # Should reject the next one
        assert session.check_rate_limit() is False

    def test_session_expiry(self):
        session = _ChatSession("test-id")
        # Manually make it expired
        session.updated_at = session.updated_at - _SESSION_EXPIRY_SECONDS - 1
        assert session.is_expired()


class TestSessionManager:
    def test_create_new_session(self):
        mgr = SessionManager()
        session = mgr.get_or_create(None)
        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_get_existing_session(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("session-123")
        s2 = mgr.get_or_create("session-123")
        assert s1 is s2

    def test_get_expired_session_creates_new(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("session-456")
        # Expire it
        s1.updated_at = s1.updated_at - _SESSION_EXPIRY_SECONDS - 1
        s2 = mgr.get_or_create("session-456")
        assert s2 is not s1

    def test_get_nonexistent_returns_none(self):
        mgr = SessionManager()
        assert mgr.get("does-not-exist") is None

    def test_get_expired_returns_none(self):
        mgr = SessionManager()
        s = mgr.get_or_create("session-789")
        s.updated_at = s.updated_at - _SESSION_EXPIRY_SECONDS - 1
        assert mgr.get("session-789") is None

    def test_delete_existing(self):
        mgr = SessionManager()
        mgr.get_or_create("to-delete")
        assert mgr.delete("to-delete") is True
        assert mgr.get("to-delete") is None

    def test_delete_nonexistent(self):
        mgr = SessionManager()
        assert mgr.delete("nope") is False

    def test_cleanup_expired(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("active")
        s2 = mgr.get_or_create("expired")
        s2.updated_at = s2.updated_at - _SESSION_EXPIRY_SECONDS - 1
        count = mgr.cleanup_expired()
        assert count == 1
        assert mgr.get("active") is s1
        assert mgr.get("expired") is None


# ---------------------------------------------------------------------------
# Chat service tests
# ---------------------------------------------------------------------------


class TestAIChatServiceChat:
    @pytest.mark.asyncio
    async def test_chat_returns_response(self, service, mock_agent_router):
        result = await service.chat("What APIs are available?")
        assert isinstance(result, ChatResponse)
        assert result.message.role == "assistant"
        assert result.message.content == "Agent says: here are your APIs."
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_chat_returns_citations(self, service, mock_agent_router):
        result = await service.chat("Find payment APIs", session_id="sess-1")
        assert result.message.citations is not None
        assert result.message.citations[0].title == "Payments API"

    @pytest.mark.asyncio
    async def test_chat_preserves_session_id(self, service, mock_agent_router):
        result = await service.chat("Hello", session_id="my-session")
        assert result.session_id == "my-session"

    @pytest.mark.asyncio
    async def test_chat_dispatches_to_agent_router(self, service, mock_agent_router):
        """dispatch() is called and its result is returned."""
        await service.chat("Find payment APIs", session_id="sess-1")
        mock_agent_router.dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_passes_accessible_api_ids_to_router(self, service, mock_agent_router):
        """accessible_api_ids is forwarded in the AgentRequest."""
        from apic_vibe_portal_bff.agents.types import AgentRequest

        await service.chat("Find APIs", accessible_api_ids=["api-a", "api-b"])
        call_args = mock_agent_router.dispatch.call_args
        req: AgentRequest = call_args.args[0]
        assert req.accessible_api_ids == ["api-a", "api-b"]

    @pytest.mark.asyncio
    async def test_chat_rate_limit(self, service):
        session = service.session_manager.get_or_create("rate-test")
        for _ in range(_RATE_LIMIT_PER_SESSION):
            session.check_rate_limit()
        with pytest.raises(ChatRateLimitError):
            await service.chat("One more", session_id="rate-test")

    @pytest.mark.asyncio
    async def test_chat_with_session_id(self, service):
        r1 = await service.chat("Hello", session_id="sess-1")
        r2 = await service.chat("Follow up", session_id="sess-1")
        assert r1.session_id == "sess-1"
        assert r2.session_id == "sess-1"


class TestAIChatServiceStream:
    @pytest.mark.asyncio
    async def test_stream_dispatches_to_agent_router(self, service, mock_agent_router):
        """chat_stream() uses dispatch() and emits start / content / end events."""
        events = [e async for e in service.chat_stream("Find APIs", session_id="sess-stream")]
        mock_agent_router.dispatch.assert_called_once()
        assert any('"type": "start"' in e for e in events)
        assert any('"type": "content"' in e for e in events)
        assert any('"type": "end"' in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_includes_citations_in_end_event(self, service, mock_agent_router):
        events = [e async for e in service.chat_stream("Find APIs", session_id="sess-stream-2")]
        end_event = next(e for e in events if '"type": "end"' in e)
        assert "Payments API" in end_event

    @pytest.mark.asyncio
    async def test_stream_error_yields_error_event(self, service, mock_agent_router):
        mock_agent_router.dispatch.side_effect = RuntimeError("Agent exploded")
        events = [e async for e in service.chat_stream("Find APIs", session_id="sess-err")]
        assert any('"type": "error"' in e for e in events)

    @pytest.mark.asyncio
    async def test_stream_includes_session_id(self, service, mock_agent_router):
        events = [e async for e in service.chat_stream("Hello", session_id="stream-sess")]
        start_event = [e for e in events if '"type": "start"' in e][0]
        assert '"stream-sess"' in start_event

    @pytest.mark.asyncio
    async def test_stream_rate_limit_returns_error(self, service):
        session = service.session_manager.get_or_create("stream-rl")
        for _ in range(_RATE_LIMIT_PER_SESSION):
            session.check_rate_limit()

        events = [e async for e in service.chat_stream("Too fast", session_id="stream-rl")]
        assert len(events) == 1
        assert '"error"' in events[0]


class TestAIChatServiceHistory:
    def test_get_history_empty(self, service):
        messages = service.get_history("no-such-session")
        assert messages == []

    @pytest.mark.asyncio
    async def test_get_history_after_chat(self, service):
        await service.chat("Hello", session_id="hist-1")
        messages = service.get_history("hist-1")
        assert len(messages) == 2  # user + assistant
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_get_history_returns_stable_ids(self, service):
        """Consecutive get_history calls return the same IDs and timestamps."""
        await service.chat("Hello", session_id="stable-1")
        msgs1 = service.get_history("stable-1")
        msgs2 = service.get_history("stable-1")
        assert len(msgs1) == len(msgs2) == 2
        for m1, m2 in zip(msgs1, msgs2, strict=True):
            assert m1.id == m2.id
            assert m1.timestamp == m2.timestamp

    @pytest.mark.asyncio
    async def test_clear_history(self, service):
        await service.chat("Hello", session_id="clear-1")
        assert service.clear_history("clear-1") is True
        assert service.get_history("clear-1") == []

    def test_clear_nonexistent(self, service):
        assert service.clear_history("nope") is False

    @pytest.mark.asyncio
    async def test_clear_history_calls_provider_clear(self, mock_agent_router):
        """clear_history should also call the history provider's clear method."""
        mock_provider = MagicMock()
        mock_provider.clear = MagicMock()
        svc = AIChatService(
            agent_router=mock_agent_router,
            history_provider=mock_provider,
        )
        await svc.chat("Hello", session_id="prov-clear")
        svc.clear_history("prov-clear")
        mock_provider.clear.assert_called_once_with("prov-clear")


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


class TestAIChatServiceConstructor:
    def test_agent_router_required(self):
        """agent_router=None raises ValueError."""
        with pytest.raises(ValueError, match="agent_router is required"):
            AIChatService(agent_router=None)


class TestAIChatServiceContentFilter:
    @pytest.mark.asyncio
    async def test_stream_agent_content_filter_yields_specific_error(self, service, mock_agent_router):
        from apic_vibe_portal_bff.clients.openai_client import OpenAIContentFilterError

        mock_agent_router.dispatch.side_effect = OpenAIContentFilterError()
        events = [e async for e in service.chat_stream("Jailbreak", session_id="sess-cf")]
        error_events = [e for e in events if '"type": "error"' in e]
        assert len(error_events) == 1
        assert "content safety filter" in error_events[0].lower()
        assert "rephrase" in error_events[0].lower()
        assert "internal error" not in error_events[0].lower()
