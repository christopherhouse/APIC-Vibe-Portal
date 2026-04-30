"""Tests for :mod:`apic_backup.services.retention_service`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from apic_backup.clients.storage_client import BackupStorageClient
from apic_backup.services.metadata_service import BackupMetadataService
from apic_backup.services.retention_service import (
    RetentionPolicy,
    RetentionService,
    compute_retention_tiers,
)


def _doc(ts: datetime, *, source: str = "apic-test") -> dict:
    iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    backup_id = f"apic-backup-{iso.replace(':', '-')}"
    return {
        "id": backup_id,
        "backupId": backup_id,
        "sourceServiceName": source,
        "timestamp": iso,
        "blobName": f"{backup_id}.zip",
        "blobUrl": f"https://fake.blob/{backup_id}.zip",
        "sizeBytes": 1024,
        "counts": {"apis": 1, "versions": 0, "definitions": 0, "deployments": 0, "environments": 0},
        "retentionTiers": [],
        "status": "completed",
    }


def test_compute_retention_tiers_assigns_tiers_to_recent_backups() -> None:
    base = datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC)
    backups = [_doc(base - timedelta(hours=i)) for i in range(48)]
    policy = RetentionPolicy(hourly=24, daily=7, monthly=3, annual=1)

    keepers, to_delete = compute_retention_tiers(backups, policy)

    keeper_ids = {k.backup_id for k in keepers}
    delete_ids = {d["backupId"] for d in to_delete}
    assert keeper_ids.isdisjoint(delete_ids)

    hourly_keepers = [k for k in keepers if "hourly" in k.tiers]
    assert len(hourly_keepers) == 24

    # Latest backup should be tagged in every active tier.
    latest = max(keepers, key=lambda k: k.document["timestamp"])
    assert "hourly" in latest.tiers
    assert "daily" in latest.tiers
    assert "monthly" in latest.tiers
    assert "annual" in latest.tiers


def test_compute_retention_tiers_prunes_old_backups_outside_all_tiers() -> None:
    base = datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC)
    backups = [
        _doc(base),
        _doc(base - timedelta(hours=1)),
        # 5 years old — should not satisfy any tier with these limits.
        _doc(base - timedelta(days=365 * 5)),
    ]
    policy = RetentionPolicy(hourly=2, daily=1, monthly=1, annual=1)

    _, to_delete = compute_retention_tiers(backups, policy)
    assert len(to_delete) == 1
    assert "2021" in to_delete[0]["timestamp"]


def test_compute_retention_tiers_keeps_invalid_timestamps() -> None:
    weird = {"id": "weird", "backupId": "weird", "timestamp": "not-a-date"}
    keepers, to_delete = compute_retention_tiers([weird], RetentionPolicy())
    assert to_delete == []
    assert keepers and keepers[0].tiers == ()


def test_retention_service_deletes_pruned_backups(fake_container_client, fake_metadata_container) -> None:
    base = datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC)
    keep = _doc(base)
    prune = _doc(base - timedelta(days=365 * 5))

    fake_metadata_container.items[keep["id"]] = keep
    fake_metadata_container.items[prune["id"]] = prune

    storage = BackupStorageClient(fake_container_client)
    metadata = BackupMetadataService(fake_metadata_container)
    service = RetentionService(metadata, storage, RetentionPolicy(1, 1, 1, 1))

    stats = service.apply("apic-test")

    assert stats == {"kept": 1, "pruned": 1}
    assert prune["blobName"] in fake_container_client.deletions
    assert keep["id"] in fake_metadata_container.items
    assert prune["id"] not in fake_metadata_container.items
