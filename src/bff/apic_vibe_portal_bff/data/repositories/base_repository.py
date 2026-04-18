"""Base repository providing common CRUD, soft-delete, and pagination logic.

All concrete repositories inherit from :class:`BaseRepository` and may
override the ``_apply_migrations`` hook to run lazy schema migrations on
documents read from Cosmos DB.

Data retention is handled by **Cosmos DB native TTL**: when a document is
soft-deleted a ``ttl`` field (in seconds) is set so Cosmos DB automatically
purges it after the configured retention period.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from azure.cosmos.container import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

logger = logging.getLogger(__name__)

# Default TTL values in seconds per container.
# Containers must have ``defaultTtl: -1`` (per-document TTL enabled) in Bicep.
TTL_SECONDS = {
    "chat-sessions": 90 * 86400,  # 90 days
    "governance-snapshots": 730 * 86400,  # ~2 years
    "analytics-events": 365 * 86400,  # 1 year
}


class PaginatedResult:
    """Wrapper for a page of results plus an opaque continuation token."""

    __slots__ = ("items", "continuation_token")

    def __init__(self, items: list[dict], continuation_token: str | None) -> None:
        self.items = items
        self.continuation_token = continuation_token

    def __repr__(self) -> str:
        return f"PaginatedResult(count={len(self.items)}, has_more={self.continuation_token is not None})"


class BaseRepository:
    """Generic Cosmos DB repository with CRUD, soft-delete, and pagination.

    Parameters
    ----------
    container:
        A :class:`ContainerProxy` for the target Cosmos DB container.
    partition_key_field:
        The camelCase field name used as the logical partition key
        (e.g. ``"userId"``).
    ttl_seconds:
        Cosmos DB TTL (in seconds) applied when a document is soft-deleted.
        Defaults to the value in :data:`TTL_SECONDS` for the container, or
        ``365 * 86400`` (1 year) if unspecified.
    """

    def __init__(
        self,
        container: ContainerProxy,
        partition_key_field: str,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        self._container = container
        self._pk_field = partition_key_field
        self._ttl = ttl_seconds if ttl_seconds is not None else TTL_SECONDS.get(container.id, 365 * 86400)

    # ------------------------------------------------------------------
    # Hooks (override in subclasses)
    # ------------------------------------------------------------------

    def _apply_migrations(self, document: dict) -> dict:
        """Apply lazy schema migrations.  Default implementation is a no-op."""
        return document

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_required_partition_key(self, document: dict) -> Any:
        """Return the partition key value or raise a clear error."""
        pk_value = document.get(self._pk_field)
        if pk_value in (None, ""):
            msg = (
                f"Document is missing required partition key field "
                f"{self._pk_field!r} for container {self._container.id!r}."
            )
            raise ValueError(msg)
        return pk_value

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, document: dict) -> dict:
        """Insert a new document.  Returns the created document (with Cosmos metadata)."""
        partition_key = self._get_required_partition_key(document)
        logger.debug("Creating document %s in %s", document.get("id"), self._container.id)
        return self._container.create_item(body=document, partition_key=partition_key)

    def find_by_id(self, item_id: str, partition_key: str) -> dict | None:
        """Point-read a single document by ID and partition key.

        Returns ``None`` when the document does not exist or is soft-deleted.
        """
        try:
            doc = self._container.read_item(item=item_id, partition_key=partition_key)
        except CosmosResourceNotFoundError:
            return None

        if doc.get("isDeleted"):
            return None

        return self._apply_migrations(doc)

    def find_by_partition_key(
        self,
        partition_key: str,
        *,
        max_items: int = 25,
        continuation_token: str | None = None,
        order_by: str | None = None,
        extra_filters: str = "",
    ) -> PaginatedResult:
        """Query documents within a single logical partition.

        Soft-deleted documents are excluded automatically.
        """
        where = f"c.{self._pk_field} = @pk AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false)"
        if extra_filters:
            where = f"{where} AND ({extra_filters})"

        query = f"SELECT * FROM c WHERE {where}"
        if order_by:
            query = f"{query} ORDER BY {order_by}"

        parameters: list[dict[str, Any]] = [{"name": "@pk", "value": partition_key}]

        pager = self._container.query_items(
            query=query,
            parameters=parameters,
            partition_key=partition_key,
            max_item_count=max_items,
        )

        page = pager.by_page(continuation_token)
        try:
            raw_items = list(next(page))  # type: ignore[arg-type]
        except StopIteration:
            raw_items = []

        items = [self._apply_migrations(doc) for doc in raw_items]
        next_token: str | None = page.continuation_token  # type: ignore[union-attr]
        return PaginatedResult(items=items, continuation_token=next_token)

    def update(self, document: dict) -> dict:
        """Replace an existing document (full replace)."""
        pk_value = self._get_required_partition_key(document)
        logger.debug("Updating document %s in %s", document.get("id"), self._container.id)
        return self._container.replace_item(item=document["id"], body=document, partition_key=pk_value)

    def soft_delete(self, item_id: str, partition_key: str) -> dict | None:
        """Mark a document as soft-deleted and set a Cosmos DB TTL for automatic purge.

        The ``ttl`` field tells Cosmos DB to permanently delete the document
        after the configured retention period (see :data:`TTL_SECONDS`).

        Returns the updated document or ``None`` if not found.
        """
        doc = self.find_by_id(item_id, partition_key)
        if doc is None:
            return None

        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        doc["isDeleted"] = True
        doc["deletedAt"] = now
        doc["ttl"] = self._ttl
        return self.update(doc)

    def hard_delete(self, item_id: str, partition_key: str) -> bool:
        """Permanently remove a document.  Returns ``True`` on success."""
        try:
            self._container.delete_item(item=item_id, partition_key=partition_key)
            return True
        except CosmosResourceNotFoundError:
            return False
