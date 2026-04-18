"""Repository for analytics event documents.

Container: ``analytics-events``, partition key: ``/eventType``.
"""

from __future__ import annotations

from azure.cosmos.container import ContainerProxy

from apic_vibe_portal_bff.data.models.analytics import CURRENT_SCHEMA_VERSION
from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository, PaginatedResult


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
