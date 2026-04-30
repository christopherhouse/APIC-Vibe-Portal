"""Cosmos DB metadata service for backup records.

Encapsulates all Cosmos DB I/O so the backup service stays focused on the
ZIP creation pipeline and the retention service stays focused on policy
evaluation.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from apic_backup.models.backup_metadata import BackupMetadata

logger = logging.getLogger(__name__)


class _ContainerLike(Protocol):
    def create_item(self, body: dict) -> dict: ...
    def upsert_item(self, body: dict) -> dict: ...
    def query_items(self, query: str, *args: Any, **kwargs: Any) -> Any: ...
    def delete_item(self, item: str, partition_key: str) -> None: ...


class BackupMetadataService:
    """CRUD operations for the ``backup-metadata`` container."""

    def __init__(self, container: _ContainerLike) -> None:
        self._container = container

    def save(self, metadata: BackupMetadata) -> dict:
        """Insert a new backup metadata document.

        Uses ``create_item`` (not ``upsert_item``) so the Cosmos
        ``uniqueKeyPolicy`` on ``/backupId`` surfaces collisions as
        ``CosmosResourceExistsError`` instead of silently overwriting an
        existing document.
        """
        doc = metadata.to_document()
        logger.info("Persisting backup metadata", extra={"backup_id": metadata.backup_id})
        return self._container.create_item(body=doc)

    def list_all(self, source_service_name: str) -> list[dict]:
        """Return successfully completed metadata documents for a source service, newest first.

        Failed backups are intentionally excluded so the retention pipeline
        cannot delete an audit record for a run that produced no blob.
        Use :meth:`list_recent_with_failures` for the admin/UI listing that
        needs visibility into failures.
        """
        query = "SELECT * FROM c WHERE c.sourceServiceName = @s AND c.status = 'completed' ORDER BY c.timestamp DESC"
        params = [{"name": "@s", "value": source_service_name}]
        items = list(
            self._container.query_items(
                query=query,
                parameters=params,
                partition_key=source_service_name,
            )
        )
        return items

    def list_recent_with_failures(self, source_service_name: str, *, limit: int = 100) -> list[dict]:
        """Return recent metadata documents (completed AND failed) for a source service."""
        query = (
            "SELECT TOP @limit * FROM c WHERE c.sourceServiceName = @s "
            "AND c.status IN ('completed', 'failed') ORDER BY c.timestamp DESC"
        )
        params = [
            {"name": "@s", "value": source_service_name},
            {"name": "@limit", "value": int(limit)},
        ]
        return list(
            self._container.query_items(
                query=query,
                parameters=params,
                partition_key=source_service_name,
            )
        )

    def delete(self, backup_id: str, source_service_name: str) -> None:
        """Delete a metadata document (idempotent)."""
        try:
            self._container.delete_item(item=backup_id, partition_key=source_service_name)
            logger.info("Deleted backup metadata", extra={"backup_id": backup_id})
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to delete backup metadata (continuing)",
                extra={"backup_id": backup_id, "error": str(exc)},
            )

    def update_retention_tiers(
        self,
        backup_id: str,
        source_service_name: str,
        tiers: list[str],
    ) -> None:
        """Update retentionTiers on an existing metadata document."""
        try:
            doc = self._container.read_item(  # type: ignore[attr-defined]
                item=backup_id,
                partition_key=source_service_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not read backup metadata for tier update",
                extra={"backup_id": backup_id, "error": str(exc)},
            )
            return
        doc["retentionTiers"] = tiers
        self._container.upsert_item(body=doc)
