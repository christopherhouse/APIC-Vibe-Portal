"""Repository for governance snapshot documents.

Container: ``governance-snapshots``, partition key: ``/apiId``.
"""

from __future__ import annotations

from azure.cosmos.container import ContainerProxy

from apic_vibe_portal_bff.data.models.governance import CURRENT_SCHEMA_VERSION
from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository, PaginatedResult, _make_ru_hook


class GovernanceRepository(BaseRepository):
    """Data access for the ``governance-snapshots`` container."""

    _MIGRATIONS: dict = {}

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container, partition_key_field="apiId")

    def _apply_migrations(self, document: dict) -> dict:
        from apic_vibe_portal_bff.data.migrations.lazy_migration import apply_migrations

        return apply_migrations(document, target_version=CURRENT_SCHEMA_VERSION, migrations=self._MIGRATIONS)

    def find_snapshots_for_api(
        self,
        api_id: str,
        *,
        max_items: int = 25,
        continuation_token: str | None = None,
    ) -> PaginatedResult:
        """Return governance snapshots for an API, newest first."""
        return self.find_by_partition_key(
            api_id,
            max_items=max_items,
            continuation_token=continuation_token,
            order_by="c.timestamp DESC",
        )

    def list_latest_snapshots(self) -> list[dict]:
        """Return the most recent non-deleted snapshot for every API.

        Executes a cross-partition query ordered by ``timestamp DESC`` and
        de-duplicates in memory so that exactly one document per ``apiId``
        is returned (the newest one).

        Returns
        -------
        list[dict]
            Snapshot documents, one per distinct API, ordered by ``timestamp``
            descending.  An empty list is returned when no snapshots exist.
        """
        query = "SELECT * FROM c WHERE (NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false) ORDER BY c.timestamp DESC"
        items = list(
            self._container.query_items(
                query=query,
                enable_cross_partition_query=True,
                response_hook=_make_ru_hook(self._container.id, "query"),
            )
        )
        # De-duplicate: keep only the first (latest) snapshot per apiId.
        seen: set[str] = set()
        latest: list[dict] = []
        for doc in items:
            api_id = doc.get("apiId", "")
            if api_id and api_id not in seen:
                seen.add(api_id)
                latest.append(self._apply_migrations(doc))
        return latest
