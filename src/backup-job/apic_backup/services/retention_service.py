"""Backup retention policy enforcement (grandfather-father-son).

Given a list of backup metadata documents and a retention configuration,
:func:`compute_retention_tiers` returns:
    - the list of backups to KEEP, each tagged with the tiers it satisfies
    - the list of backups to DELETE (no tier matches)

The pure-function design (no I/O) makes the policy easy to unit test.  The
:class:`RetentionService` wraps the function with the side effects required
to actually delete blobs and metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from apic_backup.clients.storage_client import BackupStorageClient
from apic_backup.services.metadata_service import BackupMetadataService

logger = logging.getLogger(__name__)

TIER_HOURLY = "hourly"
TIER_DAILY = "daily"
TIER_MONTHLY = "monthly"
TIER_ANNUAL = "annual"


@dataclass(frozen=True)
class RetentionPolicy:
    hourly: int = 24
    daily: int = 30
    monthly: int = 12
    annual: int = 3


@dataclass(frozen=True)
class TieredBackup:
    """A backup metadata document plus the retention tiers it satisfies."""

    document: dict
    tiers: tuple[str, ...]

    @property
    def backup_id(self) -> str:
        return str(self.document.get("backupId") or self.document.get("id", ""))

    @property
    def source_service_name(self) -> str:
        return str(self.document.get("sourceServiceName", ""))

    @property
    def blob_name(self) -> str:
        return str(self.document.get("blobName", ""))


def _parse_timestamp(doc: dict) -> datetime | None:
    raw = doc.get("timestamp")
    if not raw:
        return None
    try:
        # ISO 8601 — strip trailing 'Z' so fromisoformat handles it on all py versions.
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_retention_tiers(
    backups: list[dict],
    policy: RetentionPolicy,
) -> tuple[list[TieredBackup], list[dict]]:
    """Tag each backup with the tiers it satisfies and split into keep/delete lists.

    Backups must be provided sorted newest first; the function will sort defensively.

    Returns
    -------
    tuple[list[TieredBackup], list[dict]]
        ``(keepers, to_delete)`` where ``keepers`` are tagged with their tiers
        and ``to_delete`` are the original documents that match no tier.
    """
    # Filter out backups without a parseable timestamp — they can't be evaluated.
    parsed: list[tuple[datetime, dict]] = []
    untagged_invalid: list[dict] = []
    for doc in backups:
        ts = _parse_timestamp(doc)
        if ts is None:
            untagged_invalid.append(doc)
            continue
        parsed.append((ts, doc))

    # Sort newest first.
    parsed.sort(key=lambda pair: pair[0], reverse=True)

    # Hourly: simply take the first N (latest) backups overall.
    hourly_set = {id(doc) for _, doc in parsed[: policy.hourly]}

    # Daily / Monthly / Annual: keep the *latest* backup for each distinct
    # day / month / year, up to N entries.
    def _bucket_keep(buckets_seen: list[str], latest_n: int, key_fn) -> set[int]:
        keep: set[int] = set()
        seen: dict[str, int] = {}
        for ts, doc in parsed:
            key = key_fn(ts)
            if key in seen:
                continue
            seen[key] = id(doc)
            if len(seen) >= latest_n:
                break
        # Keep the latest backup per bucket — order preserved by parsed sort.
        keep.update(seen.values())
        buckets_seen.extend(seen.keys())
        return keep

    daily_keep = _bucket_keep([], policy.daily, lambda ts: ts.strftime("%Y-%m-%d"))
    monthly_keep = _bucket_keep([], policy.monthly, lambda ts: ts.strftime("%Y-%m"))
    annual_keep = _bucket_keep([], policy.annual, lambda ts: ts.strftime("%Y"))

    keepers: list[TieredBackup] = []
    to_delete: list[dict] = []

    for _, doc in parsed:
        tiers: list[str] = []
        doc_id = id(doc)
        if doc_id in hourly_set:
            tiers.append(TIER_HOURLY)
        if doc_id in daily_keep:
            tiers.append(TIER_DAILY)
        if doc_id in monthly_keep:
            tiers.append(TIER_MONTHLY)
        if doc_id in annual_keep:
            tiers.append(TIER_ANNUAL)
        if tiers:
            keepers.append(TieredBackup(document=doc, tiers=tuple(tiers)))
        else:
            to_delete.append(doc)

    # Backups with invalid timestamps are kept (don't risk deleting unparseable
    # records) but receive no tier assignments.
    for doc in untagged_invalid:
        keepers.append(TieredBackup(document=doc, tiers=()))

    return keepers, to_delete


class RetentionService:
    """Apply the retention policy to a backup catalog."""

    def __init__(
        self,
        metadata_service: BackupMetadataService,
        storage_client: BackupStorageClient,
        policy: RetentionPolicy,
    ) -> None:
        self._metadata = metadata_service
        self._storage = storage_client
        self._policy = policy

    def apply(self, source_service_name: str) -> dict[str, int]:
        """Evaluate retention for ``source_service_name`` and prune accordingly.

        Returns
        -------
        dict
            Counters for ``kept``, ``pruned``.
        """
        documents = self._metadata.list_all(source_service_name)
        keepers, to_delete = compute_retention_tiers(documents, self._policy)

        for keeper in keepers:
            current_tiers = list(keeper.document.get("retentionTiers") or [])
            new_tiers = list(keeper.tiers)
            if sorted(current_tiers) != sorted(new_tiers):
                self._metadata.update_retention_tiers(
                    keeper.backup_id,
                    keeper.source_service_name,
                    new_tiers,
                )

        for doc in to_delete:
            backup_id = str(doc.get("backupId") or doc.get("id", ""))
            blob_name = str(doc.get("blobName", ""))
            if blob_name:
                self._storage.delete_backup(blob_name)
            if backup_id:
                self._metadata.delete(backup_id, source_service_name)

        logger.info(
            "Retention pass complete",
            extra={
                "source": source_service_name,
                "kept": len(keepers),
                "pruned": len(to_delete),
            },
        )
        return {"kept": len(keepers), "pruned": len(to_delete)}
