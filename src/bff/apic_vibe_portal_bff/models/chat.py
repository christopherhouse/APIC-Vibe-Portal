"""Pydantic models for the chat API.

Mirrors the shared TypeScript DTOs:
  - ``ChatRequest``  → ``src/shared/src/dto/chat-request.ts``
  - ``ChatResponse`` → ``src/shared/src/dto/chat-response.ts``
  - ``ChatMessage``  → ``src/shared/src/models/chat-message.ts``
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class Citation(BaseModel):
    """A citation referencing an API in the catalog."""

    title: str = Field(..., description="Title of the cited API or document")
    url: str | None = Field(default=None, description="URL to the API detail page")
    content: str | None = Field(default=None, description="Excerpt from the source content")


class ChatMessage(BaseModel):
    """A single chat message mirroring the shared ChatMessage type."""

    id: str = Field(..., description="Unique message identifier")
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message text content")
    citations: list[Citation] | None = Field(default=None, description="Citations to APIs in the catalog")
    timestamp: str = Field(..., description="ISO-8601 timestamp")


# ---------------------------------------------------------------------------
# Request / Response DTOs
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    session_id: str | None = Field(default=None, alias="sessionId", description="Session ID for continuity")
    message: str = Field(..., min_length=1, max_length=4000, description="User message")

    model_config = {"populate_by_name": True}


class ChatResponse(BaseModel):
    """Response body for the synchronous chat endpoint."""

    session_id: str = Field(..., alias="sessionId", description="Session identifier")
    message: ChatMessage = Field(..., description="Assistant response message")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class ChatHistoryResponse(BaseModel):
    """Response body for the chat history endpoint."""

    session_id: str = Field(..., alias="sessionId", description="Session identifier")
    messages: list[ChatMessage] = Field(default_factory=list, description="Ordered messages in the session")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}
