"""Data retention via Cosmos DB native TTL.

Retention is handled automatically by Cosmos DB: each container has
``defaultTtl: -1`` (per-document TTL) and the ``soft_delete`` method
on :class:`BaseRepository` sets a ``ttl`` field on the document.  Cosmos
DB then purges the document after the TTL expires — no custom cleanup
job is needed.

This module documents the retention periods for reference.

Retention periods (from ``docs/architecture/data-retention-policy.md``):

* Chat sessions — 90 days
* Governance snapshots — 2 years (730 days)
* Analytics events — 1 year (365 days)
"""

# Re-export the TTL constants from the repository module for convenience.
from apic_vibe_portal_bff.data.repositories.base_repository import TTL_SECONDS

__all__ = ["TTL_SECONDS"]
