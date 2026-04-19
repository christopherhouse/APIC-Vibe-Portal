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
from apic_vibe_portal_bff.clients.openai_client import OpenAIClientError
from apic_vibe_portal_bff.middleware.rbac import require_any_role
from apic_vibe_portal_bff.middleware.security_trimming import make_accessible_ids_dep
from apic_vibe_portal_bff.models.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from apic_vibe_portal_bff.services.ai_chat_service import AIChatService, ChatRateLimitError
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service dependency — lazily created once per process
# ---------------------------------------------------------------------------

_service_instance: AIChatService | None = None


def _get_chat_service() -> AIChatService:
    """Return a shared :class:`AIChatService` instance.

    In production the service is created once with a real agent router
    backed by Azure AI Foundry and an optional ``CosmosHistoryProvider``
    for Cosmos DB-backed chat history.
    Tests override this dependency via ``app.dependency_overrides``.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        from apic_vibe_portal_bff.config.settings import get_settings

        settings = get_settings()
        search_client = AISearchClient(
            endpoint=settings.ai_search_endpoint,
            index_name=settings.ai_search_index_name,
        )

        # Wire up MAF CosmosHistoryProvider if Cosmos DB is configured
        history_provider = None
        if settings.cosmos_db_endpoint.strip():
            try:
                from agent_framework.azure import CosmosHistoryProvider
                from azure.identity import DefaultAzureCredential

                history_provider = CosmosHistoryProvider(
                    endpoint=settings.cosmos_db_endpoint,
                    database_name=settings.cosmos_db_database_name,
                    container_name=settings.cosmos_db_chat_container,
                    credential=DefaultAzureCredential(),
                )
                logger.info("Using MAF CosmosHistoryProvider for chat history")
            except Exception:
                logger.exception("Failed to initialise CosmosHistoryProvider — falling back to InMemoryHistoryProvider")

        # Wire up the agent router — required for chat to function.
        # Fail fast if Foundry is not configured or init fails.
        if not settings.foundry_project_endpoint.strip():
            raise RuntimeError(
                "FOUNDRY_PROJECT_ENDPOINT is not configured — set this environment variable to enable the agent router"
            )

        from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
        from apic_vibe_portal_bff.agents.agent_router import AgentRouter
        from apic_vibe_portal_bff.agents.api_discovery_agent.definition import ApiDiscoveryAgent
        from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
        from apic_vibe_portal_bff.clients.foundry_agent_client import FoundryAgentClient

        foundry_client = FoundryAgentClient(
            project_endpoint=settings.foundry_project_endpoint,
            deployment=settings.openai_chat_deployment,
        )
        api_center_client = ApiCenterClient(
            base_url=settings.api_center_endpoint,
            workspace_name=settings.api_center_workspace_name,
        )
        discovery_agent = ApiDiscoveryAgent(
            maf_client=foundry_client.get_maf_client(),
            search_client=search_client,
            api_center_client=api_center_client,
            history_provider=history_provider,
            model=settings.openai_chat_deployment,
        )
        registry = AgentRegistry()
        registry.register(discovery_agent)
        agent_router = AgentRouter(registry)
        logger.info("Agent router initialised with Foundry endpoint=%s", settings.foundry_project_endpoint)

        _service_instance = AIChatService(
            agent_router=agent_router,
            history_provider=history_provider,
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
async def chat(
    request: ChatRequest,
    service: AIChatService = Depends(_get_chat_service),  # noqa: B008
    accessible_api_ids: list[str] | None = Depends(make_accessible_ids_dep()),  # noqa: B008
) -> ChatResponse:
    """Send a chat message and receive an AI-generated response.

    The response is grounded in the API catalog via RAG retrieval.  The RAG
    context is restricted to APIs the authenticated user may access so the AI
    cannot reference inaccessible APIs.
    """
    try:
        return await service.chat(
            user_message=request.message,
            session_id=request.session_id,
            accessible_api_ids=accessible_api_ids,
        )
    except ChatRateLimitError:
        _raise_error(429, "RATE_LIMIT_EXCEEDED", "Too many messages. Please wait before sending another.")
    except OpenAIClientError as exc:
        safe_error = sanitize_for_log(str(exc))
        safe_session = sanitize_for_log(request.session_id or "")
        logger.error(
            "Chat failed — status=%s error=%s",
            exc.status_code,
            safe_error,
            extra={
                "status_code": exc.status_code,
                "error_code": getattr(exc, "code", None),
                "error_message": safe_error,
                "session_id": safe_session,
            },
        )
        _raise_error(exc.status_code or 500, "CHAT_ERROR", safe_error)


@router.post(
    "/api/chat/stream",
    dependencies=[Depends(require_any_role(_ALLOWED_ROLES))],
)
async def chat_stream(
    request: ChatRequest,
    service: AIChatService = Depends(_get_chat_service),  # noqa: B008
    accessible_api_ids: list[str] | None = Depends(make_accessible_ids_dep()),  # noqa: B008
) -> StreamingResponse:
    """Send a chat message and receive a streaming SSE response.

    Tokens are streamed as they are generated, with a final event
    containing citations and metadata.  The RAG context is restricted to
    APIs the authenticated user may access.
    """
    return StreamingResponse(
        service.chat_stream(
            user_message=request.message,
            session_id=request.session_id,
            accessible_api_ids=accessible_api_ids,
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
