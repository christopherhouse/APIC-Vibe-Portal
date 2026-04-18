"""Chat API endpoints.

Exposes the RAG-powered AI chat interface:

POST   /api/chat            — Send a message and receive a response
POST   /api/chat/stream     — Send a message and receive a streaming SSE response
GET    /api/chat/history     — Retrieve conversation history for a session
DELETE /api/chat/history     — Clear conversation history for a session
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from apic_vibe_portal_bff.clients.ai_search_client import AISearchClient
from apic_vibe_portal_bff.clients.openai_client import OpenAIClient, OpenAIClientError
from apic_vibe_portal_bff.middleware.rbac import require_any_role
from apic_vibe_portal_bff.models.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from apic_vibe_portal_bff.services.ai_chat_service import AIChatService, ChatRateLimitError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service dependency — lazily created once per process
# ---------------------------------------------------------------------------

_service_instance: AIChatService | None = None


def _get_chat_service() -> AIChatService:
    """Return a shared :class:`AIChatService` instance.

    In production the service is created once with real Azure credentials.
    Tests override this dependency via ``app.dependency_overrides``.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()
        openai_client = OpenAIClient(
            endpoint=settings.openai_endpoint,
            deployment=settings.openai_chat_deployment,
        )
        search_client = AISearchClient(
            endpoint=settings.ai_search_endpoint,
            index_name=settings.ai_search_index_name,
        )
        _service_instance = AIChatService(
            openai_client=openai_client,
            search_client=search_client,
            model=settings.openai_chat_deployment,
        )
    return _service_instance


# ---------------------------------------------------------------------------
# Error models
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    details: Any | None = None


class ChatApiErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail


class ChatApiError(Exception):
    """Raised by route handlers to produce a structured error response."""

    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def chat_api_error_handler(_request: object, exc: ChatApiError) -> JSONResponse:
    """Serialize :class:`ChatApiError` into a JSON error envelope."""
    body = ChatApiErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_ROLES = ["Portal.User", "Portal.Admin", "Portal.Maintainer"]


def _raise_error(status_code: int, code: str, message: str, details: Any | None = None) -> None:
    """Raise a :class:`ChatApiError` with a structured error body."""
    raise ChatApiError(status_code=status_code, code=code, message=message, details=details)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["chat"])


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def chat(
    request: ChatRequest,
    service: AIChatService = Depends(_get_chat_service),  # noqa: B008
) -> ChatResponse:
    """Send a chat message and receive an AI-generated response.

    The response is grounded in the API catalog via RAG retrieval.
    """
    try:
        return service.chat(
            user_message=request.message,
            session_id=request.session_id,
        )
    except ChatRateLimitError:
        _raise_error(429, "RATE_LIMIT_EXCEEDED", "Too many messages. Please wait before sending another.")
    except OpenAIClientError as exc:
        logger.error("Chat failed — status=%s error=%s", exc.status_code, str(exc))
        _raise_error(exc.status_code or 500, "CHAT_ERROR", str(exc))


@router.post(
    "/api/chat/stream",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def chat_stream(
    request: ChatRequest,
    service: AIChatService = Depends(_get_chat_service),  # noqa: B008
) -> StreamingResponse:
    """Send a chat message and receive a streaming SSE response.

    Tokens are streamed as they are generated, with a final event
    containing citations and metadata.
    """
    return StreamingResponse(
        service.chat_stream(
            user_message=request.message,
            session_id=request.session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/api/chat/history",
    response_model=ChatHistoryResponse,
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def get_chat_history(
    session_id: str = Query(..., alias="sessionId", description="Session ID"),  # noqa: B008
    service: AIChatService = Depends(_get_chat_service),  # noqa: B008
) -> ChatHistoryResponse:
    """Retrieve conversation history for a session."""
    messages = service.get_history(session_id)
    return ChatHistoryResponse(
        sessionId=session_id,
        messages=messages,
    )


@router.delete(
    "/api/chat/history",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
def clear_chat_history(
    session_id: str = Query(..., alias="sessionId", description="Session ID"),  # noqa: B008
    service: AIChatService = Depends(_get_chat_service),  # noqa: B008
) -> dict[str, Any]:
    """Clear conversation history for a session."""
    deleted = service.clear_history(session_id)
    return {"deleted": deleted, "sessionId": session_id}
