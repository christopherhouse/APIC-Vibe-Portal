"""Tests for the RAG-powered AI chat service."""

from __future__ import annotations

from unittest.mock import MagicMock

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
    estimate_messages_tokens,
    estimate_tokens,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_openai():
    """Return a mock OpenAI client."""
    client = MagicMock()
    client.chat_completion.return_value = {
        "content": "The Weather API provides real-time weather data.",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 30,
            "total_tokens": 130,
        },
    }
    return client


@pytest.fixture
def mock_search():
    """Return a mock AI Search client."""
    client = MagicMock()
    client.search.return_value = {
        "results": [
            {
                "apiName": "weather-api",
                "title": "Weather API",
                "description": "Provides real-time weather data for any location.",
                "kind": "REST",
                "lifecycleStage": "Production",
            },
            {
                "apiName": "maps-api",
                "title": "Maps API",
                "description": "Geocoding and mapping services.",
                "kind": "REST",
                "lifecycleStage": "Production",
            },
        ],
        "count": 2,
        "facets": None,
    }
    return client


@pytest.fixture
def service(mock_openai, mock_search):
    """Return an AIChatService with mock dependencies."""
    return AIChatService(
        openai_client=mock_openai,
        search_client=mock_search,
        model="gpt-4o",
    )


# ---------------------------------------------------------------------------
# Token estimation tests
# ---------------------------------------------------------------------------


class TestTokenEstimation:
    def test_estimate_tokens_nonempty(self):
        tokens = estimate_tokens("Hello world, how are you?")
        assert tokens > 0

    def test_estimate_tokens_empty(self):
        tokens = estimate_tokens("")
        assert tokens == 0

    def test_estimate_messages_tokens(self):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0
        # Should be more than the sum of individual texts due to overhead
        individual = estimate_tokens("You are a helpful assistant.") + estimate_tokens("Hello")
        assert tokens > individual

    def test_estimate_tokens_fallback_model(self):
        # Unknown model should fall back to cl100k_base
        tokens = estimate_tokens("Hello world", model="unknown-model-xyz")
        assert tokens > 0


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
    def test_chat_returns_response(self, service, mock_openai, mock_search):
        result = service.chat("What APIs are available?")
        assert isinstance(result, ChatResponse)
        assert result.message.role == "assistant"
        assert result.message.content == "The Weather API provides real-time weather data."
        assert result.session_id is not None

    def test_chat_includes_citations(self, service):
        result = service.chat("Tell me about the Weather API")
        assert result.message.citations is not None
        assert len(result.message.citations) > 0
        assert any("Weather API" in c.title for c in result.message.citations)

    def test_chat_with_session_id(self, service):
        r1 = service.chat("Hello", session_id="sess-1")
        r2 = service.chat("Follow up", session_id="sess-1")
        assert r1.session_id == "sess-1"
        assert r2.session_id == "sess-1"

    def test_chat_calls_search(self, service, mock_search):
        service.chat("Find me APIs")
        mock_search.search.assert_called_once()
        call_kwargs = mock_search.search.call_args
        assert call_kwargs.kwargs.get("query_type") == "semantic"

    def test_chat_calls_openai(self, service, mock_openai):
        service.chat("Hello")
        mock_openai.chat_completion.assert_called_once()

    def test_chat_with_no_search_results(self, service, mock_search):
        mock_search.search.return_value = {"results": [], "count": 0, "facets": None}
        result = service.chat("Something obscure")
        assert isinstance(result, ChatResponse)
        assert result.message.citations is None or len(result.message.citations) == 0

    def test_chat_search_failure_continues(self, service, mock_search):
        from apic_vibe_portal_bff.clients.ai_search_client import AISearchClientError

        mock_search.search.side_effect = AISearchClientError("Search down")
        result = service.chat("Hello")
        # Should still return a response, just without citations
        assert isinstance(result, ChatResponse)

    def test_chat_rate_limit(self, service):
        # Exhaust the rate limit
        session = service.session_manager.get_or_create("rate-test")
        for _ in range(_RATE_LIMIT_PER_SESSION):
            session.check_rate_limit()
        # Next chat should raise
        with pytest.raises(ChatRateLimitError):
            service.chat("One more", session_id="rate-test")


class TestAIChatServiceStream:
    def test_stream_yields_events(self, service, mock_openai):
        mock_openai.chat_completion_stream.return_value = iter(
            [
                {"content": "Hello", "finish_reason": None},
                {"content": " world", "finish_reason": "stop"},
                {
                    "content": "",
                    "finish_reason": None,
                    "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
                },
            ]
        )

        events = list(service.chat_stream("Hello"))
        # Should have: start, content, content, end
        assert any('"type": "start"' in e for e in events)
        assert any('"type": "content"' in e for e in events)
        assert any('"type": "end"' in e for e in events)

    def test_stream_includes_session_id(self, service, mock_openai):
        mock_openai.chat_completion_stream.return_value = iter(
            [
                {"content": "Test", "finish_reason": "stop"},
            ]
        )

        events = list(service.chat_stream("Hello", session_id="stream-sess"))
        start_event = [e for e in events if '"type": "start"' in e][0]
        assert '"stream-sess"' in start_event

    def test_stream_rate_limit_returns_error(self, service):
        session = service.session_manager.get_or_create("stream-rl")
        for _ in range(_RATE_LIMIT_PER_SESSION):
            session.check_rate_limit()

        events = list(service.chat_stream("Too fast", session_id="stream-rl"))
        assert len(events) == 1
        assert '"error"' in events[0]

    def test_stream_mid_stream_error_yields_error_event(self, service, mock_openai):
        """If streaming raises mid-response, an SSE error event is emitted."""

        def failing_stream(*args, **kwargs):
            yield {"content": "Partial", "finish_reason": None}
            raise RuntimeError("Connection dropped")

        mock_openai.chat_completion_stream.return_value = failing_stream()
        events = list(service.chat_stream("Hello"))
        # Should have: start, content (partial), error
        assert any('"type": "start"' in e for e in events)
        assert any('"type": "error"' in e for e in events)
        # Should NOT have an "end" event
        assert not any('"type": "end"' in e for e in events)


class TestAIChatServiceHistory:
    def test_get_history_empty(self, service):
        messages = service.get_history("no-such-session")
        assert messages == []

    def test_get_history_after_chat(self, service):
        service.chat("Hello", session_id="hist-1")
        messages = service.get_history("hist-1")
        assert len(messages) == 2  # user + assistant
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_get_history_returns_stable_ids(self, service):
        """Consecutive get_history calls return the same IDs and timestamps."""
        service.chat("Hello", session_id="stable-1")
        msgs1 = service.get_history("stable-1")
        msgs2 = service.get_history("stable-1")
        assert len(msgs1) == len(msgs2) == 2
        for m1, m2 in zip(msgs1, msgs2, strict=True):
            assert m1.id == m2.id
            assert m1.timestamp == m2.timestamp

    def test_clear_history(self, service):
        service.chat("Hello", session_id="clear-1")
        assert service.clear_history("clear-1") is True
        assert service.get_history("clear-1") == []

    def test_clear_nonexistent(self, service):
        assert service.clear_history("nope") is False

    def test_clear_history_calls_provider_clear(self, mock_openai, mock_search):
        """clear_history should also call the history provider's clear method."""
        mock_provider = MagicMock()
        mock_provider.clear = MagicMock()
        svc = AIChatService(
            openai_client=mock_openai,
            search_client=mock_search,
            history_provider=mock_provider,
        )
        svc.chat("Hello", session_id="prov-clear")
        svc.clear_history("prov-clear")
        mock_provider.clear.assert_called_once_with("prov-clear")


# ---------------------------------------------------------------------------
# RAG context retrieval
# ---------------------------------------------------------------------------


class TestRAGContextRetrieval:
    def test_retrieve_context_builds_citations(self, service, mock_search):
        context, citations = service._retrieve_context("weather")
        assert len(citations) == 2
        assert "Weather API" in citations[0].title
        assert citations[0].url == "/api/catalog/weather-api"

    def test_retrieve_context_text_includes_api_info(self, service):
        context, _ = service._retrieve_context("weather")
        assert "Weather API" in context
        assert "REST" in context

    def test_retrieve_context_search_failure(self, service, mock_search):
        from apic_vibe_portal_bff.clients.ai_search_client import AISearchClientError

        mock_search.search.side_effect = AISearchClientError("Unavailable")
        context, citations = service._retrieve_context("weather")
        assert context == ""
        assert citations == []


# ---------------------------------------------------------------------------
# OTel metrics emission
# ---------------------------------------------------------------------------


class TestMetricEmission:
    def test_emit_token_metrics(self, service):
        # Should not raise
        service._emit_token_metrics(
            estimated_tokens=100,
            usage={"prompt_tokens": 95, "completion_tokens": 30, "total_tokens": 125},
        )

    def test_emit_token_metrics_large_drift_warning(self, service, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            service._emit_token_metrics(
                estimated_tokens=100,
                usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            )
        assert any("Token estimate drift" in r.message for r in caplog.records)

    def test_emit_token_metrics_zero_estimated(self, service):
        # Should not raise even with zero estimated
        service._emit_token_metrics(
            estimated_tokens=0,
            usage={"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
        )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


class TestPromptConstruction:
    def test_build_messages_includes_system_prompt(self, service):
        session = _ChatSession("test")
        messages = service._build_messages(session, "Hello", "")
        assert messages[0]["role"] == "system"
        assert "API Discovery Assistant" in messages[0]["content"]

    def test_build_messages_includes_context(self, service):
        session = _ChatSession("test")
        messages = service._build_messages(session, "Hello", "Some API context here")
        # Should have a system context message containing the injected context
        context_msgs = [m for m in messages if m["role"] == "system" and "Some API context here" in m["content"]]
        assert len(context_msgs) == 1

    def test_build_messages_includes_user_message(self, service):
        session = _ChatSession("test")
        messages = service._build_messages(session, "What APIs exist?", "")
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "What APIs exist?"

    def test_build_messages_includes_history(self, service):
        session = _ChatSession("test")
        session.add_message("user", "Previous question")
        session.add_message("assistant", "Previous answer")
        messages = service._build_messages(session, "Follow up", "")
        # Should include history between system and new user message
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) == 2  # previous + current


# ---------------------------------------------------------------------------
# MAF history provider integration tests
# ---------------------------------------------------------------------------


class TestMAFHistoryProvider:
    def test_default_uses_in_memory_provider(self, mock_openai, mock_search):
        """When no history_provider is given, InMemoryHistoryProvider is used."""
        service = AIChatService(
            openai_client=mock_openai,
            search_client=mock_search,
        )
        from agent_framework import InMemoryHistoryProvider

        assert isinstance(service._history_provider, InMemoryHistoryProvider)

    def test_custom_history_provider_is_stored(self, mock_openai, mock_search):
        """A custom history_provider is accepted and stored."""
        mock_provider = MagicMock()
        service = AIChatService(
            openai_client=mock_openai,
            search_client=mock_search,
            history_provider=mock_provider,
        )
        assert service._history_provider is mock_provider

    def test_service_creates_search_tool(self, service):
        """The MAF search tool is created during init."""
        assert service._search_tool is not None

    def test_service_creates_agent(self, service):
        """The MAF Agent is created during init and wired with tools."""
        from agent_framework import Agent

        assert service._agent is not None
        assert isinstance(service._agent, Agent)
