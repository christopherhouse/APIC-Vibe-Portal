"""Repository for analytics event documents.

Container: ``analytics-events``, partition key: ``/eventType``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from azure.cosmos.container import ContainerProxy

from apic_vibe_portal_bff.data.models.analytics import CURRENT_SCHEMA_VERSION
from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository, PaginatedResult

logger = logging.getLogger(__name__)


class AnalyticsRepository(BaseRepository):
    """Data access for the ``analytics-events`` container."""

    _MIGRATIONS: dict = {}

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container, partition_key_field="eventType")

    def _apply_migrations(self, document: dict) -> dict:
        from apic_vibe_portal_bff.data.migrations.lazy_migration import apply_migrations

        return apply_migrations(document, target_version=CURRENT_SCHEMA_VERSION, migrations=self._MIGRATIONS)

    def find_events_by_type(
        self,
        event_type: str,
        *,
        max_items: int = 50,
        continuation_token: str | None = None,
    ) -> PaginatedResult:
        """Return analytics events of a given type, newest first."""
        return self.find_by_partition_key(
            event_type,
            max_items=max_items,
            continuation_token=continuation_token,
            order_by="c.timestamp DESC",
        )

    # ------------------------------------------------------------------
    # Aggregation queries (cross-partition)
    # ------------------------------------------------------------------

    def _query_cross_partition(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a cross-partition query and return all results."""
        items = self._container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=True,
        )
        return list(items)

    def count_events_by_type(self, event_type: str, *, days: int) -> int:
        """Count events of a given type within the last *days* days."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = self._query_cross_partition(
            "SELECT VALUE COUNT(1) FROM c WHERE c.eventType = @et AND c.timestamp >= @since "
            "AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false)",
            [{"name": "@et", "value": event_type}, {"name": "@since", "value": since}],
        )
        return rows[0] if rows else 0

    def count_distinct_users(self, *, days: int) -> int:
        """Count distinct user IDs across all event types within *days* days."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = self._query_cross_partition(
            "SELECT VALUE COUNT(1) FROM ("
            "  SELECT DISTINCT c.userId FROM c "
            "  WHERE c.timestamp >= @since AND c.userId != '' "
            "  AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false)"
            ")",
            [{"name": "@since", "value": since}],
        )
        return rows[0] if rows else 0

    def daily_event_counts(self, event_type: str, *, days: int) -> list[dict[str, Any]]:
        """Return per-day counts for a given event type over *days* days."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        return self._query_cross_partition(
            "SELECT SUBSTRING(c.timestamp, 0, 10) AS date, COUNT(1) AS count "
            "FROM c WHERE c.eventType = @et AND c.timestamp >= @since "
            "AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false) "
            "GROUP BY SUBSTRING(c.timestamp, 0, 10)",
            [{"name": "@et", "value": event_type}, {"name": "@since", "value": since}],
        )

    def daily_active_users(self, *, days: int) -> list[dict[str, Any]]:
        """Return per-day distinct user counts over *days* days."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        return self._query_cross_partition(
            "SELECT dates.date, COUNT(1) AS count FROM ("
            "  SELECT DISTINCT c.userId, SUBSTRING(c.timestamp, 0, 10) AS date "
            "  FROM c WHERE c.timestamp >= @since AND c.userId != '' "
            "  AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false)"
            ") AS dates GROUP BY dates.date",
            [{"name": "@since", "value": since}],
        )

    def top_viewed_apis(self, *, days: int, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most-viewed APIs (by api_view event count)."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = self._query_cross_partition(
            "SELECT c.apiId, COUNT(1) AS viewCount "
            "FROM c WHERE c.eventType = 'api_view' AND c.timestamp >= @since "
            "AND c.apiId != '' "
            "AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false) "
            "GROUP BY c.apiId",
            [{"name": "@since", "value": since}],
        )
        rows.sort(key=lambda r: r.get("viewCount", 0), reverse=True)
        return rows[:limit]

    def top_downloaded_apis(self, *, days: int) -> dict[str, int]:
        """Return download counts per API."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = self._query_cross_partition(
            "SELECT c.apiId, COUNT(1) AS downloadCount "
            "FROM c WHERE c.eventType = 'spec_download' AND c.timestamp >= @since "
            "AND c.apiId != '' "
            "AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false) "
            "GROUP BY c.apiId",
            [{"name": "@since", "value": since}],
        )
        return {r["apiId"]: r.get("downloadCount", 0) for r in rows}

    def chat_mention_counts(self, *, days: int) -> dict[str, int]:
        """Return chat interaction counts per session (proxy for API mentions)."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = self._query_cross_partition(
            "SELECT c.apiId, COUNT(1) AS mentionCount "
            "FROM c WHERE c.eventType = 'chat_interaction' AND c.timestamp >= @since "
            "AND c.apiId != '' "
            "AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false) "
            "GROUP BY c.apiId",
            [{"name": "@since", "value": since}],
        )
        return {r["apiId"]: r.get("mentionCount", 0) for r in rows}

    def search_daily_volume(self, *, days: int) -> list[dict[str, Any]]:
        """Return per-day search query counts."""
        return self.daily_event_counts("search_query", days=days)

    def feature_usage_counts(self, *, days: int) -> dict[str, int]:
        """Return counts per event type for feature adoption metrics."""
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        rows = self._query_cross_partition(
            "SELECT c.eventType, COUNT(1) AS count "
            "FROM c WHERE c.timestamp >= @since "
            "AND (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false) "
            "GROUP BY c.eventType",
            [{"name": "@since", "value": since}],
        )
        return {r["eventType"]: r.get("count", 0) for r in rows}
