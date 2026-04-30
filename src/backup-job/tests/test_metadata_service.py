"""Tests for :mod:`apic_backup.services.metadata_service`."""

from __future__ import annotations

import pytest
from azure.cosmos.exceptions import CosmosResourceExistsError

from apic_backup.models.backup_manifest import ManifestCounts
from apic_backup.models.backup_metadata import BackupMetadata
from apic_backup.services.metadata_service import BackupMetadataService


def _metadata(backup_id: str = "apic-backup-2026-04-28T12-00-00Z") -> BackupMetadata:
    return BackupMetadata(
        id=backup_id,
        backupId=backup_id,
        sourceServiceName="apic-test",
        timestamp="2026-04-28T12:00:00Z",
        blobUrl=f"https://fake.blob/{backup_id}.zip",
        blobName=f"{backup_id}.zip",
        sizeBytes=4096,
        counts=ManifestCounts(apis=2, versions=2, definitions=2, deployments=2, environments=1),
        retentionTiers=["hourly"],
        status="completed",
        durationMs=1234,
    )


def test_save_persists_document_with_aliases(fake_metadata_container) -> None:
    service = BackupMetadataService(fake_metadata_container)
    md = _metadata()

    service.save(md)

    saved = fake_metadata_container.items[md.id]
    assert saved["backupId"] == md.backup_id
    assert saved["sourceServiceName"] == "apic-test"
    assert saved["sizeBytes"] == 4096
    assert saved["retentionTiers"] == ["hourly"]


def test_list_all_returns_existing_documents(fake_metadata_container) -> None:
    service = BackupMetadataService(fake_metadata_container)
    md = _metadata()
    service.save(md)

    items = service.list_all("apic-test")
    assert len(items) == 1
    assert items[0]["backupId"] == md.backup_id


def test_delete_is_idempotent(fake_metadata_container) -> None:
    service = BackupMetadataService(fake_metadata_container)
    md = _metadata()
    service.save(md)

    service.delete(md.backup_id, "apic-test")
    service.delete(md.backup_id, "apic-test")  # should not raise

    assert md.id not in fake_metadata_container.items


def test_update_retention_tiers_rewrites_field(fake_metadata_container) -> None:
    service = BackupMetadataService(fake_metadata_container)
    md = _metadata()
    service.save(md)

    service.update_retention_tiers(md.backup_id, "apic-test", ["hourly", "daily"])
    assert fake_metadata_container.items[md.id]["retentionTiers"] == ["hourly", "daily"]


def test_save_raises_on_duplicate_backup_id(fake_metadata_container) -> None:
    """N2 — switching to create_item surfaces collisions instead of silently overwriting."""
    service = BackupMetadataService(fake_metadata_container)
    md = _metadata()
    service.save(md)
    with pytest.raises(CosmosResourceExistsError):
        service.save(md)


def test_list_recent_with_failures_includes_failed_documents(fake_metadata_container) -> None:
    """C3 — admin listing must surface failed runs."""
    service = BackupMetadataService(fake_metadata_container)
    completed = _metadata("apic-backup-2026-04-28T12-00-00Z-aa")
    failed = _metadata("apic-backup-2026-04-28T13-00-00Z-bb")
    service.save(completed)
    failed_doc = failed.to_document()
    failed_doc["status"] = "failed"
    failed_doc["error"] = "boom"
    fake_metadata_container.items[failed_doc["id"]] = failed_doc

    items = service.list_recent_with_failures("apic-test", limit=10)
    statuses = sorted(i["status"] for i in items)
    assert statuses == ["completed", "failed"]


def test_backup_metadata_extra_fields_ignored() -> None:
    """M3 — model_config extra='ignore' silently drops unknown fields."""
    md = BackupMetadata.model_validate(
        {
            "id": "x",
            "backupId": "x",
            "sourceServiceName": "s",
            "timestamp": "2026-04-28T12:00:00Z",
            "blobUrl": "u",
            "blobName": "n",
            "sizeBytes": 1,
            "counts": {},
            "totallyMadeUpField": "ignored",
        }
    )
    doc = md.to_document()
    assert "totallyMadeUpField" not in doc
