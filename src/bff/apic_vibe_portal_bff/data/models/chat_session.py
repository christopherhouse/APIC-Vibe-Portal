"""Pydantic models for chat session documents in Cosmos DB.

Documents are stored in the ``chat-sessions`` container, partitioned by
``/userId``.  Every document carries a ``schemaVersion`` field to support
lazy migration (see :mod:`apic_vibe_portal_bff.data.migrations.lazy_migration`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class ChatMessageDoc(BaseModel):
    """A single message within a chat session document."""

    id: str = Field(..., description="Unique message identifier")
    role: str = Field(..., description="Message role: user | assistant | system")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(..., description="ISO-8601 timestamp of the message")


# ---------------------------------------------------------------------------
# Chat session document
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION: int = 1


class ChatSessionDocument(BaseModel):
    """Cosmos DB document schema for a chat session."""

    id: str = Field(..., description="Unique session identifier (UUID)")
    user_id: str = Field(..., alias="userId", description="Owner user ID (partition key)")
    title: str = Field(default="", description="Session title")
    messages: list[ChatMessageDoc] = Field(default_factory=list, description="Ordered messages in the session")
    created_at: str = Field(..., alias="createdAt", description="ISO-8601 creation timestamp")
    updated_at: str = Field(..., alias="updatedAt", description="ISO-8601 last-update timestamp")
    model: str | None = Field(default=None, description="AI model used for this session")
    tokens_used: int = Field(default=0, alias="tokensUsed", description="Total tokens consumed")
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, alias="schemaVersion")
    is_deleted: bool = Field(default=False, alias="isDeleted", description="Soft-delete flag")
    deleted_at: str | None = Field(default=None, alias="deletedAt", description="ISO-8601 soft-delete timestamp")

    model_config = {"populate_by_name": True}

    def to_cosmos_dict(self) -> dict:
        """Serialise to a dict using camelCase alias keys for Cosmos DB storage."""
        return self.model_dump(by_alias=True, exclude_none=False)

    @classmethod
    def new(
        cls,
        *,
        session_id: str,
        user_id: str,
        title: str = "",
        model: str | None = None,
    ) -> ChatSessionDocument:
        """Factory helper that creates a new session with timestamps set to *now*."""
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return cls(
            id=session_id,
            userId=user_id,
            title=title,
            messages=[],
            createdAt=now,
            updatedAt=now,
            model=model,
            tokensUsed=0,
            schemaVersion=CURRENT_SCHEMA_VERSION,
            isDeleted=False,
            deletedAt=None,
        )
