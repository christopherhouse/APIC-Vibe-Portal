"""Core backup pipeline.

Enumerates every entity in an Azure API Center service, packages them into a
ZIP archive with the structure documented in
``docs/project/plan/034-api-center-backup.md``, uploads the archive to blob
storage, and writes a metadata document to Cosmos DB.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import tempfile
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
    """Return a backup ID like ``apic-backup-2026-04-28T12-00-00Z-ab12``.

    The 4-character hex suffix prevents sub-second collisions if two runs
    are triggered close together.
    """
    sanitised = now_iso.replace(":", "-")
    suffix = secrets.token_hex(2)  # 4 hex characters
    return f"apic-backup-{sanitised}-{suffix}"


def _detect_spec_extension(spec_content: str | None, definition: dict[str, Any]) -> str:
    """Best-effort detection of the file extension to use for a spec payload.

    Inspects the actual ``spec_content`` when available rather than relying
    on the API Center ``specification.name`` enum (``openapi``, ``asyncapi``,
    ``wsdl``, ``grpc``, …) which never contains ``yaml``.
    """
    if spec_content:
        sample = spec_content.lstrip()
        if sample.startswith("{") or sample.startswith("["):
            return "json"
        # WSDL is XML
        if sample.startswith("<?xml") or sample.startswith("<"):
            spec_name = str(definition.get("specification", {}).get("name") or "").lower()
            if "wsdl" in spec_name:
                return "wsdl"
            return "xml"
        # YAML — OpenAPI / AsyncAPI / Swagger declarations at column 0
        for marker in ("openapi:", "swagger:", "asyncapi:"):
            if sample.startswith(marker) or f"\n{marker}" in sample:
                return "yaml"
        # GraphQL schema files commonly start with `schema {` or `type `
        spec_name = str(definition.get("specification", {}).get("name") or "").lower()
        if "graphql" in spec_name or sample.startswith(("schema ", "type ")):
            return "graphql"
        # Default to YAML for anything else that isn't JSON/XML
        return "yaml"

    # No content available — fall back to the definition hint
    spec_type = str(
        definition.get("specification", {}).get("name") or definition.get("specificationFormat") or "json"
    ).lower()
    if "wsdl" in spec_type:
        return "wsdl"
    if "graphql" in spec_type:
        return "graphql"
    return "json"


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
        """Produce, upload, and persist a single backup.

        On any unhandled exception, a ``status="failed"`` metadata document
        is persisted (best-effort) before the exception is re-raised so the
        admin UI surfaces failed runs.
        """
        start = time.monotonic()
        now_iso = _now_iso()
        backup_id = _backup_id(now_iso)
        blob_name = f"{backup_id}.zip"

        logger.info("Backup starting", extra={"backup_id": backup_id})

        try:
            counts = ManifestCounts()
            tmp_path, size_bytes = self._build_zip_to_tempfile(now_iso=now_iso, counts=counts)
            try:
                # Azure Blob metadata names must follow C# identifier rules
                # (letters, digits, underscores only — no hyphens). See:
                # https://learn.microsoft.com/azure/storage/blobs/storage-blob-container-properties-metadata
                manifest_metadata = {
                    "backup_timestamp": now_iso,
                    "api_count": str(counts.apis),
                    "entity_count": str(counts.total_entities),
                    "backup_version": "1.0",
                }
                with open(tmp_path, "rb") as fh:
                    blob_url = self._storage.upload_backup_stream(
                        blob_name=blob_name,
                        stream=fh,
                        length=size_bytes,
                        metadata=manifest_metadata,
                    )
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    logger.debug("Failed to unlink temp backup file %s", tmp_path)

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
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception("Backup failed", extra={"backup_id": backup_id, "duration_ms": duration_ms})
            failure = BackupMetadata(
                id=backup_id,
                backupId=backup_id,
                sourceServiceName=self._source.service_name,
                timestamp=now_iso,
                blobUrl="",
                blobName="",
                sizeBytes=0,
                counts=ManifestCounts(),
                retentionTiers=[],
                status="failed",
                durationMs=duration_ms,
                error=repr(exc)[:2000],
            )
            try:
                self._metadata.save(failure)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Failed to persist failure metadata document",
                    extra={"backup_id": backup_id},
                )
            raise

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_zip_to_tempfile(self, *, now_iso: str, counts: ManifestCounts) -> tuple[str, int]:
        """Stream the ZIP archive to a temp file; return (path, size_bytes)."""
        fd, tmp_path = tempfile.mkstemp(suffix=".zip", prefix="apic-backup-")
        os.close(fd)
        try:
            with open(tmp_path, "wb") as fh, zipfile.ZipFile(fh, "w", compression=zipfile.ZIP_DEFLATED) as zf:
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
            size_bytes = os.path.getsize(tmp_path)
            return tmp_path, size_bytes
        except Exception:
            # Don't leak the temp file if ZIP construction failed
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

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
        apis: list[dict] = self._apic.list_apis() or []

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
                ext = _detect_spec_extension(spec, definition)
                zf.writestr(f"{def_base}/spec.{ext}", spec)

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
