"""Tests for the chat API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apic_vibe_portal_bff.app import create_app
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.models.chat import ChatMessage, ChatResponse
from apic_vibe_portal_bff.routers.chat import _get_chat_service
from apic_vibe_portal_bff.services.ai_chat_service import AIChatService, ChatRateLimitError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MOCK_USER = AuthenticatedUser(
    oid="test-user",
    name="Test User",
    email="test@example.com",
    roles=["Portal.User"],
    claims={},
)

_AUTH_HEADERS = {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_chat_service():
    """Return a mock AIChatService."""
    svc = MagicMock(spec=AIChatService)
    svc.chat.return_value = ChatResponse(
        sessionId="test-session-123",
        message=ChatMessage(
            id="msg-1",
            role="assistant",
            content="The Weather API provides real-time weather data.",
            citations=[],
            timestamp="2026-04-18T00:00:00Z",
        ),
    )
    svc.get_history.return_value = [
        ChatMessage(
            id="msg-1",
            role="user",
            content="What APIs?",
            timestamp="2026-04-18T00:00:00Z",
        ),
        ChatMessage(
            id="msg-2",
            role="assistant",
            content="Here are some APIs.",
            timestamp="2026-04-18T00:00:01Z",
        ),
    ]
    svc.clear_history.return_value = True
    return svc


@pytest.fixture
def chat_app(mock_chat_service):
    """Return a FastAPI app with the chat service overridden."""
    app = create_app()
    app.dependency_overrides[_get_chat_service] = lambda: mock_chat_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def chat_client(chat_app):
    """Return an async test client for the chat endpoints."""
    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_chat_success(self, mock_validate, chat_client, mock_chat_service):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.post(
            "/api/chat",
            json={"message": "What APIs are available?"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sessionId"] == "test-session-123"
        assert body["message"]["role"] == "assistant"
        assert "Weather API" in body["message"]["content"]

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_chat_with_session_id(self, mock_validate, chat_client, mock_chat_service):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.post(
            "/api/chat",
            json={"message": "Follow up", "sessionId": "existing-session"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 200
        mock_chat_service.chat.assert_called_once_with(
            user_message="Follow up",
            session_id="existing-session",
            accessible_api_ids=[],
        )

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_chat_empty_message_rejected(self, mock_validate, chat_client):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.post(
            "/api/chat",
            json={"message": ""},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 422  # Validation error

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_chat_rate_limit(self, mock_validate, chat_client, mock_chat_service):
        mock_validate.return_value = _MOCK_USER
        mock_chat_service.chat.side_effect = ChatRateLimitError("sess-1")
        response = await chat_client.post(
            "/api/chat",
            json={"message": "Too fast"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 429

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_chat_openai_error(self, mock_validate, chat_client, mock_chat_service):
        from apic_vibe_portal_bff.clients.openai_client import OpenAIClientError

        mock_validate.return_value = _MOCK_USER
        mock_chat_service.chat.side_effect = OpenAIClientError("Service error", status_code=500)
        response = await chat_client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 500

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_chat_content_filter_error(self, mock_validate, chat_client, mock_chat_service):
        from apic_vibe_portal_bff.clients.openai_client import OpenAIContentFilterError

        mock_validate.return_value = _MOCK_USER
        mock_chat_service.chat.side_effect = OpenAIContentFilterError()
        response = await chat_client.post(
            "/api/chat",
            json={"message": "Bad prompt"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "CONTENT_FILTER"
        assert "content safety filter" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# POST /api/chat/stream
# ---------------------------------------------------------------------------


class TestChatStreamEndpoint:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_stream_returns_sse(self, mock_validate, chat_client, mock_chat_service):
        mock_validate.return_value = _MOCK_USER

        def fake_stream(user_message, session_id=None):
            yield 'data: {"type": "start", "sessionId": "s1"}\n\n'
            yield 'data: {"type": "content", "content": "Hello"}\n\n'
            yield 'data: {"type": "end", "message": {}, "sessionId": "s1"}\n\n'

        mock_chat_service.chat_stream.return_value = fake_stream("Hello")

        response = await chat_client.post(
            "/api/chat/stream",
            json={"message": "Hello"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


# ---------------------------------------------------------------------------
# GET /api/chat/history
# ---------------------------------------------------------------------------


class TestGetChatHistory:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_get_history(self, mock_validate, chat_client, mock_chat_service):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.get(
            "/api/chat/history?sessionId=sess-1",
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sessionId"] == "sess-1"
        assert len(body["messages"]) == 2

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_get_history_missing_session_id(self, mock_validate, chat_client):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.get(
            "/api/chat/history",
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 422  # Missing required query param


# ---------------------------------------------------------------------------
# DELETE /api/chat/history
# ---------------------------------------------------------------------------


class TestClearChatHistory:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_clear_history(self, mock_validate, chat_client, mock_chat_service):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.delete(
            "/api/chat/history?sessionId=sess-1",
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["deleted"] is True
        assert body["sessionId"] == "sess-1"

    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_clear_history_missing_session_id(self, mock_validate, chat_client):
        mock_validate.return_value = _MOCK_USER
        response = await chat_client.delete(
            "/api/chat/history",
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Chat API error handler
# ---------------------------------------------------------------------------


class TestChatApiErrorHandler:
    @patch("apic_vibe_portal_bff.middleware.auth.validate_token")
    async def test_error_handler_formats_response(self, mock_validate, chat_client, mock_chat_service):
        from apic_vibe_portal_bff.routers.chat import ChatApiError

        mock_validate.return_value = _MOCK_USER
        mock_chat_service.chat.side_effect = ChatApiError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="OpenAI is down",
        )
        response = await chat_client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers=_AUTH_HEADERS,
        )
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
