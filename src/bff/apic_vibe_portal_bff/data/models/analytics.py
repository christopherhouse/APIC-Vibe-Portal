"""Pydantic models for analytics event documents in Cosmos DB.

Documents are stored in the ``analytics-events`` container, partitioned
by ``/eventType``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Analytics event document
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION: int = 1


class AnalyticsEventDocument(BaseModel):
    """Cosmos DB document schema for an analytics event."""

    id: str = Field(..., description="Unique event identifier (UUID)")
    event_type: str = Field(..., alias="eventType", description="Event type (partition key)")
    timestamp: str = Field(..., description="ISO-8601 event timestamp")
    user_id: str = Field(default="", alias="userId", description="Hashed user identifier")
    api_id: str = Field(default="", alias="apiId", description="Related API identifier (if applicable)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event-specific payload")
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
        event_id: str,
        event_type: str,
        user_id: str = "",
        api_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AnalyticsEventDocument:
        """Factory helper that creates a new event with timestamp set to *now*."""
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return cls(
            id=event_id,
            eventType=event_type,
            timestamp=now,
            userId=user_id,
            apiId=api_id,
            metadata=metadata or {},
            schemaVersion=CURRENT_SCHEMA_VERSION,
            isDeleted=False,
            deletedAt=None,
        )
