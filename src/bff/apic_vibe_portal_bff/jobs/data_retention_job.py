"""Data retention cleanup job.

Permanently deletes soft-deleted documents that have exceeded their
configured retention period.  Intended to be invoked on a daily schedule
(e.g. via Azure Container Apps Job or an external cron trigger).

Retention periods (from ``docs/architecture/data-retention-policy.md``):

* Chat sessions — 90 days
* Governance snapshots — 2 years (730 days)
* Analytics events — 1 year (365 days)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

# Default retention days per container
RETENTION_DAYS = {
    "chat-sessions": 90,
    "governance-snapshots": 730,
    "analytics-events": 365,
}


def run_cleanup(
    repositories: dict[str, BaseRepository],
    *,
    retention_overrides: dict[str, int] | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Purge expired soft-deleted documents from all repositories.

    Parameters
    ----------
    repositories:
        Mapping of container name → :class:`BaseRepository` instance.
    retention_overrides:
        Optional dict overriding the default retention days per container.
    now:
        Override the current time (useful for testing).

    Returns
    -------
    dict[str, int]
        Mapping of container name → number of documents purged.
    """
    effective_now = now or datetime.utcnow()
    retentions = dict(RETENTION_DAYS)
    if retention_overrides:
        retentions.update(retention_overrides)

    results: dict[str, int] = {}

    for container_name, repo in repositories.items():
        days = retentions.get(container_name, 365)
        cutoff = (effective_now - timedelta(days=days)).isoformat() + "Z"
        logger.info("Cleaning %s: purging soft-deleted before %s (%d-day retention)", container_name, cutoff, days)

        expired = repo.find_expired_soft_deleted(cutoff)
        purged = 0
        for doc in expired:
            pk = doc.get(repo._pk_field, "")
            if repo.hard_delete(doc["id"], pk):
                purged += 1

        results[container_name] = purged
        logger.info("Purged %d documents from %s", purged, container_name)

    return results
