"""Tests for :mod:`apic_backup.services.backup_service`."""

from __future__ import annotations

import io
import json
import re
import zipfile

import pytest

from apic_backup.clients.storage_client import BackupStorageClient
from apic_backup.models.backup_manifest import ManifestSource
from apic_backup.services.backup_service import (
    BackupService,
    _backup_id,
    _detect_spec_extension,
    _entity_name,
)
from apic_backup.services.metadata_service import BackupMetadataService


def _source() -> ManifestSource:
    return ManifestSource(
        subscriptionId="sub-123",
        resourceGroup="rg-test",
        serviceName="apic-test",
        location="eastus",
    )


def test_entity_name_sanitises_unsafe_characters() -> None:
    assert _entity_name({"name": "my api/v1"}) == "my-api-v1"
    assert _entity_name({}) == "unnamed"


def test_backup_id_includes_random_suffix() -> None:
    backup_id = _backup_id("2026-04-28T12:00:00Z")
    assert re.fullmatch(r"apic-backup-2026-04-28T12-00-00Z-[0-9a-f]{4}", backup_id)


def test_backup_id_is_unique_per_call() -> None:
    ids = {_backup_id("2026-04-28T12:00:00Z") for _ in range(50)}
    # Practically guaranteed not to collide with 50 4-hex draws.
    assert len(ids) == 50


def test_backup_service_produces_well_formed_zip(
    fake_apic_client, fake_container_client, fake_metadata_container
) -> None:
    storage = BackupStorageClient(fake_container_client)
    metadata = BackupMetadataService(fake_metadata_container)
    service = BackupService(
        apic_client=fake_apic_client,
        storage_client=storage,
        metadata_service=metadata,
        source=_source(),
    )

    result = service.run()

    assert len(fake_container_client.uploads) == 1
    blob_name, payload = next(iter(fake_container_client.uploads.items()))
    assert blob_name.startswith("apic-backup-") and blob_name.endswith(".zip")
    assert payload["metadata"]["api_count"] == "2"
    assert payload["metadata"]["entity_count"] == str(result.metadata.counts.total_entities)

    with zipfile.ZipFile(io.BytesIO(payload["data"])) as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "environments/production.json" in names
        assert "environments/staging.json" in names
        assert "apis/petstore/api.json" in names
        assert "apis/petstore/versions/v1/version.json" in names
        assert "apis/petstore/versions/v1/definitions/openapi/definition.json" in names
        assert "apis/petstore/versions/v1/definitions/openapi/spec.json" in names
        assert "apis/petstore/deployments/petstore-prod.json" in names
        assert "metadata/custom-metadata-schemas.json" in names

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["format"] == "apic-backup"
        assert manifest["counts"]["apis"] == 2
        assert manifest["counts"]["versions"] == 2
        assert manifest["counts"]["definitions"] == 2
        assert manifest["counts"]["environments"] == 2

    saved = next(iter(fake_metadata_container.items.values()))
    assert saved["status"] == "completed"
    assert saved["sourceServiceName"] == "apic-test"
    assert saved["sizeBytes"] == result.size_bytes


def test_backup_service_continues_on_partial_failures(fake_container_client, fake_metadata_container) -> None:
    class _FlakyApic:
        def list_apis(self):
            return [{"name": "good"}]

        def list_api_versions(self, api_name):
            raise RuntimeError("versions API unavailable")

        def list_api_definitions(self, api_name, version_name):  # pragma: no cover
            raise AssertionError("should not be called")

        def export_api_specification(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("should not be called")

        def list_environments(self):
            raise RuntimeError("envs unavailable")

        def list_deployments(self, api_name):
            return []

    storage = BackupStorageClient(fake_container_client)
    metadata = BackupMetadataService(fake_metadata_container)
    service = BackupService(
        apic_client=_FlakyApic(),
        storage_client=storage,
        metadata_service=metadata,
        source=_source(),
    )

    result = service.run()

    # API is enumerated, version listing failed but didn't crash the run.
    assert result.metadata.counts.apis == 1
    assert result.metadata.counts.versions == 0
    assert result.metadata.counts.environments == 0
    assert result.metadata.status == "completed"


# ---------------------------------------------------------------------------
# C3 — failed backups must be persisted to Cosmos
# ---------------------------------------------------------------------------


def test_backup_service_writes_failure_doc_on_exception(fake_container_client, fake_metadata_container) -> None:
    """When list_apis() crashes, a status='failed' document must be saved."""

    class _BrokenApic:
        def list_apis(self):
            raise RuntimeError("apic data plane unreachable")

        def list_api_versions(self, api_name):  # pragma: no cover
            raise AssertionError

        def list_api_definitions(self, api_name, version_name):  # pragma: no cover
            raise AssertionError

        def export_api_specification(self, *a, **kw):  # pragma: no cover
            raise AssertionError

        def list_environments(self):
            return []

        def list_deployments(self, api_name):  # pragma: no cover
            return []

    storage = BackupStorageClient(fake_container_client)
    metadata = BackupMetadataService(fake_metadata_container)
    service = BackupService(
        apic_client=_BrokenApic(),
        storage_client=storage,
        metadata_service=metadata,
        source=_source(),
    )

    with pytest.raises(RuntimeError, match="apic data plane unreachable"):
        service.run()

    assert len(fake_metadata_container.items) == 1
    failure = next(iter(fake_metadata_container.items.values()))
    assert failure["status"] == "failed"
    assert "apic data plane unreachable" in (failure.get("error") or "")
    assert failure["blobName"] == ""
    assert failure["sizeBytes"] == 0
    assert failure["durationMs"] >= 0
    # No blob upload should have happened
    assert fake_container_client.uploads == {}


# ---------------------------------------------------------------------------
# M4 — spec extension detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content,definition,expected",
    [
        ('{"openapi": "3.0.0"}', {"specification": {"name": "openapi"}}, "json"),
        ("openapi: 3.0.0\ninfo:\n  title: x", {"specification": {"name": "openapi"}}, "yaml"),
        ("asyncapi: 2.0.0\n", {"specification": {"name": "asyncapi"}}, "yaml"),
        (
            '<?xml version="1.0"?><definitions></definitions>',
            {"specification": {"name": "wsdl"}},
            "wsdl",
        ),
        ("type Query { hello: String }", {"specification": {"name": "graphql"}}, "graphql"),
    ],
)
def test_detect_spec_extension(content, definition, expected) -> None:
    assert _detect_spec_extension(content, definition) == expected


def test_detect_spec_extension_falls_back_when_no_content() -> None:
    assert _detect_spec_extension(None, {"specification": {"name": "openapi"}}) == "json"
    assert _detect_spec_extension(None, {"specification": {"name": "wsdl"}}) == "wsdl"
