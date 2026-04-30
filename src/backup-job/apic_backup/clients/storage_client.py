"""Azure Blob Storage client for backup uploads."""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _ContainerClientLike(Protocol):
    def upload_blob(
        self,
        name: str,
        data: bytes,
        *,
        overwrite: bool = ...,
        metadata: dict[str, str] | None = ...,
        content_settings: Any | None = ...,
    ) -> Any: ...

    def delete_blob(self, blob: str) -> None: ...


class BackupStorageClient:
    """Thin wrapper around an Azure Blob ``ContainerClient``.

    The wrapper exists so the backup service does not depend directly on the
    Azure SDK and can be unit-tested with simple mocks.
    """

    def __init__(self, container_client: _ContainerClientLike) -> None:
        self._container = container_client

    def upload_backup(
        self,
        blob_name: str,
        data: bytes,
        *,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload a ZIP archive and return the blob URL."""
        try:
            from azure.storage.blob import ContentSettings

            content_settings = ContentSettings(content_type="application/zip")
        except Exception:  # noqa: BLE001
            content_settings = None

        logger.info(
            "Uploading backup blob",
            extra={"blob_name": blob_name, "size_bytes": len(data)},
        )
        result = self._container.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            metadata=metadata or {},
            content_settings=content_settings,
        )
        # ``BlobClient.url`` is the canonical URL.  Different mocks may return
        # different shapes — fall back to the blob client lookup if present.
        if hasattr(result, "url"):
            return str(result.url)
        try:
            blob_client = self._container.get_blob_client(blob_name)  # type: ignore[attr-defined]
            return str(blob_client.url)
        except Exception:  # noqa: BLE001
            return blob_name

    def delete_backup(self, blob_name: str) -> None:
        """Delete a backup blob (idempotent — missing blobs are ignored)."""
        try:
            self._container.delete_blob(blob_name)
            logger.info("Deleted backup blob", extra={"blob_name": blob_name})
        except Exception as exc:  # noqa: BLE001
            # Swallow "not found" errors so retention pruning is idempotent.
            logger.warning(
                "Failed to delete backup blob (continuing)",
                extra={"blob_name": blob_name, "error": str(exc)},
            )
