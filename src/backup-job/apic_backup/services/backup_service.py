"""Core backup pipeline.

Enumerates every entity in an Azure API Center service, packages them into a
ZIP archive with the structure documented in
``docs/project/plan/034-api-center-backup.md``, uploads the archive to blob
storage, and writes a metadata document to Cosmos DB.
"""

from __future__ import annotations

import io
import json
import logging
import time
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Protocol

from apic_backup.clients.storage_client import BackupStorageClient
from apic_backup.models.backup_manifest import (
    BackupManifest,
    ManifestCounts,
    ManifestSource,
)
from apic_backup.models.backup_metadata import BackupMetadata
from apic_backup.services.metadata_service import BackupMetadataService

logger = logging.getLogger(__name__)


class _ApiCenterClient(Protocol):
    def list_apis(self) -> list[dict[str, Any]]: ...
    def list_api_versions(self, api_name: str) -> list[dict[str, Any]]: ...
    def list_api_definitions(self, api_name: str, version_name: str) -> list[dict[str, Any]]: ...
    def export_api_specification(self, api_name: str, version_name: str, definition_name: str) -> str | None: ...
    def list_environments(self) -> list[dict[str, Any]]: ...
    def list_deployments(self, api_name: str) -> list[dict[str, Any]]: ...


def _entity_name(entity: dict[str, Any]) -> str:
    """Return a stable file-system-safe name for an API Center entity."""
    name = entity.get("name") or entity.get("id") or "unnamed"
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in str(name))
    return safe or "unnamed"


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _backup_id(now_iso: str) -> str:
    """Return a backup ID like ``apic-backup-2026-04-28T12-00-00Z``."""
    sanitised = now_iso.replace(":", "-")
    return f"apic-backup-{sanitised}"


class BackupResult:
    """Outcome of a single backup run."""

    __slots__ = ("metadata", "blob_name", "size_bytes", "duration_ms")

    def __init__(
        self,
        metadata: BackupMetadata,
        blob_name: str,
        size_bytes: int,
        duration_ms: int,
    ) -> None:
        self.metadata = metadata
        self.blob_name = blob_name
        self.size_bytes = size_bytes
        self.duration_ms = duration_ms


class BackupService:
    """Produce a single backup archive of an API Center service."""

    def __init__(
        self,
        apic_client: _ApiCenterClient,
        storage_client: BackupStorageClient,
        metadata_service: BackupMetadataService,
        *,
        source: ManifestSource,
    ) -> None:
        self._apic = apic_client
        self._storage = storage_client
        self._metadata = metadata_service
        self._source = source

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> BackupResult:
        """Produce, upload, and persist a single backup."""
        start = time.monotonic()
        now_iso = _now_iso()
        backup_id = _backup_id(now_iso)
        blob_name = f"{backup_id}.zip"

        logger.info("Backup starting", extra={"backup_id": backup_id})

        counts = ManifestCounts()
        zip_bytes = self._build_zip(now_iso=now_iso, counts=counts)
        size_bytes = len(zip_bytes)

        manifest_metadata = {
            "backup-timestamp": now_iso,
            "api-count": str(counts.apis),
            "entity-count": str(counts.total_entities),
            "backup-version": "1.0",
        }

        blob_url = self._storage.upload_backup(
            blob_name=blob_name,
            data=zip_bytes,
            metadata=manifest_metadata,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        metadata = BackupMetadata(
            id=backup_id,
            backupId=backup_id,
            sourceServiceName=self._source.service_name,
            timestamp=now_iso,
            blobUrl=blob_url,
            blobName=blob_name,
            sizeBytes=size_bytes,
            counts=counts,
            retentionTiers=[],
            status="completed",
            durationMs=duration_ms,
            error=None,
        )
        self._metadata.save(metadata)

        logger.info(
            "Backup complete",
            extra={
                "backup_id": backup_id,
                "size_bytes": size_bytes,
                "duration_ms": duration_ms,
                "counts": counts.model_dump(),
            },
        )
        return BackupResult(
            metadata=metadata,
            blob_name=blob_name,
            size_bytes=size_bytes,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_zip(self, *, now_iso: str, counts: ManifestCounts) -> bytes:
        """Enumerate API Center entities and package them into a ZIP."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            self._write_environments(zf, counts)
            self._write_apis(zf, counts)
            self._write_metadata(zf)

            manifest = BackupManifest(
                createdAt=now_iso,
                source=self._source,
                counts=counts,
            )
            zf.writestr(
                "manifest.json",
                json.dumps(manifest.model_dump(by_alias=True), indent=2),
            )
        return buf.getvalue()

    def _write_environments(self, zf: zipfile.ZipFile, counts: ManifestCounts) -> None:
        try:
            envs: Iterable[dict] = self._apic.list_environments() or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to list environments — continuing", exc_info=exc)
            envs = []
        for env in envs:
            counts.environments += 1
            zf.writestr(
                f"environments/{_entity_name(env)}.json",
                json.dumps(env, indent=2, default=str),
            )

    def _write_apis(self, zf: zipfile.ZipFile, counts: ManifestCounts) -> None:
        try:
            apis: list[dict] = self._apic.list_apis() or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to list APIs — backup will be empty", exc_info=exc)
            apis = []

        for api in apis:
            counts.apis += 1
            api_name = _entity_name(api)
            base = f"apis/{api_name}"
            zf.writestr(
                f"{base}/api.json",
                json.dumps(api, indent=2, default=str),
            )
            self._write_api_versions(zf, api_name, base, counts)
            self._write_api_deployments(zf, api_name, base, counts)

    def _write_api_versions(
        self,
        zf: zipfile.ZipFile,
        api_name: str,
        base: str,
        counts: ManifestCounts,
    ) -> None:
        try:
            versions = self._apic.list_api_versions(api_name) or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to list versions for API", extra={"api": api_name}, exc_info=exc)
            return
        for version in versions:
            counts.versions += 1
            version_name = _entity_name(version)
            version_base = f"{base}/versions/{version_name}"
            zf.writestr(
                f"{version_base}/version.json",
                json.dumps(version, indent=2, default=str),
            )
            self._write_definitions(zf, api_name, version_name, version_base, counts)

    def _write_definitions(
        self,
        zf: zipfile.ZipFile,
        api_name: str,
        version_name: str,
        version_base: str,
        counts: ManifestCounts,
    ) -> None:
        try:
            definitions = self._apic.list_api_definitions(api_name, version_name) or []
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to list definitions",
                extra={"api": api_name, "version": version_name},
                exc_info=exc,
            )
            return
        for definition in definitions:
            counts.definitions += 1
            def_name = _entity_name(definition)
            def_base = f"{version_base}/definitions/{def_name}"
            zf.writestr(
                f"{def_base}/definition.json",
                json.dumps(definition, indent=2, default=str),
            )
            try:
                spec = self._apic.export_api_specification(api_name, version_name, def_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to export specification",
                    extra={"api": api_name, "version": version_name, "definition": def_name},
                    exc_info=exc,
                )
                spec = None
            if spec:
                ext = self._spec_extension(definition)
                zf.writestr(f"{def_base}/spec.{ext}", spec)

    @staticmethod
    def _spec_extension(definition: dict) -> str:
        spec_type = str(
            definition.get("specification", {}).get("name") or definition.get("specificationFormat") or "json"
        ).lower()
        if "yaml" in spec_type or "yml" in spec_type:
            return "yaml"
        return "json"

    def _write_api_deployments(
        self,
        zf: zipfile.ZipFile,
        api_name: str,
        base: str,
        counts: ManifestCounts,
    ) -> None:
        try:
            deployments = self._apic.list_deployments(api_name) or []
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to list deployments",
                extra={"api": api_name},
                exc_info=exc,
            )
            return
        for deployment in deployments:
            counts.deployments += 1
            zf.writestr(
                f"{base}/deployments/{_entity_name(deployment)}.json",
                json.dumps(deployment, indent=2, default=str),
            )

    def _write_metadata(self, zf: zipfile.ZipFile) -> None:
        # Custom metadata schemas are not exposed via the data-plane in the
        # current API version.  Write a placeholder so restore tooling has a
        # stable path to populate when the SDK supports it.
        zf.writestr(
            "metadata/custom-metadata-schemas.json",
            json.dumps({"schemas": []}, indent=2),
        )
