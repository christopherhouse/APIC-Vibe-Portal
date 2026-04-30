"""Azure Blob Storage client for backup uploads."""

from __future__ import annotations

import logging
from typing import IO, Any, Protocol

from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class _ContainerClientLike(Protocol):
    def upload_blob(
        self,
        name: str,
        data: Any,
        *,
        overwrite: bool = ...,
        metadata: dict[str, str] | None = ...,
        content_settings: Any | None = ...,
        length: int | None = ...,
        max_concurrency: int = ...,
    ) -> Any: ...

    def delete_blob(self, blob: str) -> None: ...


def _content_settings() -> Any | None:
    try:
        from azure.storage.blob import ContentSettings

        return ContentSettings(content_type="application/zip")
    except Exception:  # noqa: BLE001
        return None


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
        """Upload a ZIP archive (in-memory ``bytes``) and return the blob URL.

        Prefer :meth:`upload_backup_stream` for production use — it streams
        from a file handle and avoids buffering the whole archive in memory.
        """
        logger.info(
            "Uploading backup blob (bytes)",
            extra={"blob_name": blob_name, "size_bytes": len(data)},
        )
        result = self._container.upload_blob(
            name=blob_name,
            data=data,
            overwrite=True,
            metadata=metadata or {},
            content_settings=_content_settings(),
        )
        return self._resolve_url(result, blob_name)

    def upload_backup_stream(
        self,
        blob_name: str,
        stream: IO[bytes],
        length: int,
        *,
        metadata: dict[str, str] | None = None,
        max_concurrency: int = 4,
    ) -> str:
        """Upload a ZIP archive from a file-like ``stream`` and return the blob URL.

        Memory-efficient: avoids loading the entire archive into Python heap
        before sending.  The Azure SDK chunks the stream into block-blob
        blocks of up to 4 MiB each.
        """
        logger.info(
            "Uploading backup blob (stream)",
            extra={"blob_name": blob_name, "size_bytes": length},
        )
        result = self._container.upload_blob(
            name=blob_name,
            data=stream,
            overwrite=True,
            metadata=metadata or {},
            content_settings=_content_settings(),
            length=length,
            max_concurrency=max_concurrency,
        )
        return self._resolve_url(result, blob_name)

    def _resolve_url(self, result: Any, blob_name: str) -> str:
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
        """Delete a backup blob.

        Idempotent for the not-found case only — any other failure is
        re-raised so callers (and operators) can see real problems instead of
        silently swallowing them.
        """
        try:
            self._container.delete_blob(blob_name)
            logger.info("Deleted backup blob", extra={"blob_name": blob_name})
        except ResourceNotFoundError:
            logger.info(
                "Blob already absent — skipping",
                extra={"blob_name": blob_name},
            )
