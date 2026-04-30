"""Backup admin service.

Reads backup metadata from Cosmos DB and generates short-lived
user-delegation SAS URLs for downloads.  The service deliberately does **not**
use account keys — Storage Blob Delegator + Blob Data Reader RBAC is
sufficient.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)

from apic_vibe_portal_bff.config.settings import get_settings
from apic_vibe_portal_bff.data.cosmos_client import get_container

logger = logging.getLogger(__name__)


class BackupNotConfiguredError(RuntimeError):
    """Raised when backup storage is not configured for this environment."""


class BackupNotFoundError(LookupError):
    """Raised when a backup ID cannot be found."""


def _format_size(size_bytes: int) -> str:
    """Return a human-readable size (KB/MB/GB)."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} PB"


class BackupService:
    """Cosmos-backed read service for the admin backup view."""

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._container = get_container(settings.cosmos_db_backup_container)
        self._credential: DefaultAzureCredential | None = None
        self._blob_service: BlobServiceClient | None = None

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_backups(
        self,
        *,
        limit: int = 50,
        continuation_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        """Return ``(items, next_continuation_token, has_more)``.

        Includes both ``status='completed'`` and ``status='failed'`` documents
        so admins can see why a recent backup didn't produce a downloadable
        archive (see plan 035, finding C3).

        When :pyattr:`apic_service_name` is configured the query is scoped to
        that partition for efficiency. If the partition key is unset, we fall
        back to a cross-partition query and emit a structured warning so the
        deployment gap is noticed quickly.
        """
        query = "SELECT * FROM c WHERE c.status IN ('completed', 'failed') ORDER BY c.timestamp DESC"
        partition_key = self._settings.apic_service_name or None
        if partition_key:
            pager = self._container.query_items(
                query=query,
                partition_key=partition_key,
                max_item_count=limit,
            )
        else:
            logger.warning(
                "Backup listing falling back to cross-partition query: "
                "APIC_SERVICE_NAME is not configured. Set it to scope the "
                "query to a single Cosmos partition.",
                extra={"event": "backup.listing.cross_partition_fallback"},
            )
            pager = self._container.query_items(
                query=query,
                enable_cross_partition_query=True,
                max_item_count=limit,
            )

        page = pager.by_page(continuation_token)
        try:
            raw_items = list(next(page))  # type: ignore[arg-type]
        except StopIteration:
            raw_items = []

        next_token: str | None = getattr(page, "continuation_token", None)
        has_more = bool(next_token)
        return [self._enrich(item) for item in raw_items], next_token, has_more

    def get_backup(self, backup_id: str) -> dict[str, Any]:
        """Return a single backup document or raise :class:`BackupNotFoundError`."""
        query = "SELECT * FROM c WHERE c.backupId = @id"
        params = [{"name": "@id", "value": backup_id}]
        try:
            items = list(
                self._container.query_items(
                    query=query,
                    parameters=params,
                    enable_cross_partition_query=True,
                )
            )
        except CosmosResourceNotFoundError as exc:
            raise BackupNotFoundError(backup_id) from exc
        if not items:
            raise BackupNotFoundError(backup_id)
        return self._enrich(items[0])

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def generate_download_url(self, backup_id: str) -> tuple[str, datetime]:
        """Return a (sas_url, expires_at) tuple for downloading the backup ZIP."""
        if not self._settings.backup_storage_account_url:
            raise BackupNotConfiguredError("BACKUP_STORAGE_ACCOUNT_URL is not configured for this environment")
        backup = self.get_backup(backup_id)
        blob_name = backup.get("blobName")
        if not blob_name:
            raise BackupNotFoundError(backup_id)

        ttl = timedelta(minutes=self._settings.backup_download_sas_ttl_minutes)
        now = datetime.now(UTC)
        expires_at = now + ttl

        blob_service = self._get_blob_service()
        # Acquire a user-delegation key via the BFF's managed identity — no
        # account keys are ever stored or transmitted.
        delegation_key = blob_service.get_user_delegation_key(
            key_start_time=now - timedelta(minutes=5),
            key_expiry_time=expires_at,
        )

        # account_name is parsed from the account URL.
        account_name = self._account_name()

        sas = generate_blob_sas(
            account_name=account_name,
            container_name=self._settings.backup_container_name,
            blob_name=blob_name,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=expires_at,
            start=now - timedelta(minutes=5),
        )
        url = (
            f"{self._settings.backup_storage_account_url.rstrip('/')}/"
            f"{self._settings.backup_container_name}/{blob_name}?{sas}"
        )
        return url, expires_at

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _enrich(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Strip Cosmos system fields and add a derived ``sizeFormatted``."""
        public = {k: v for k, v in doc.items() if not k.startswith("_")}
        size_bytes = int(public.get("sizeBytes") or 0)
        public["sizeFormatted"] = _format_size(size_bytes)
        return public

    def _get_blob_service(self) -> BlobServiceClient:
        if self._blob_service is None:
            self._credential = self._credential or DefaultAzureCredential()
            self._blob_service = BlobServiceClient(
                account_url=self._settings.backup_storage_account_url,
                credential=self._credential,
            )
        return self._blob_service

    def _account_name(self) -> str:
        # https://acct.blob.core.windows.net  ->  acct
        url = self._settings.backup_storage_account_url
        host = url.split("://", 1)[-1]
        return host.split(".", 1)[0]


_service: BackupService | None = None


def get_backup_service() -> BackupService:
    """Lazily-initialised singleton accessor for FastAPI DI."""
    global _service  # noqa: PLW0603
    if _service is None:
        _service = BackupService()
    return _service


def reset_backup_service() -> None:  # pragma: no cover - test helper
    """Reset the cached service (used by tests)."""
    global _service  # noqa: PLW0603
    _service = None
