"""Lazy schema migration utility.

Applies a chain of version-to-version migration functions to a Cosmos DB
document so that the application always works with the current schema.
Documents are **not** written back automatically — the caller decides when
to persist the updated document (typically on the next update).

Usage
-----
>>> from apic_vibe_portal_bff.data.migrations.lazy_migration import apply_migrations
>>> doc = {"schemaVersion": 1, "id": "abc", ...}
>>> MIGRATIONS = {1: migrate_v1_to_v2}
>>> migrated = apply_migrations(doc, target_version=2, migrations=MIGRATIONS)
>>> assert migrated["schemaVersion"] == 2
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

MigrationFn = Callable[[dict], dict]


def apply_migrations(
    document: dict,
    *,
    target_version: int,
    migrations: dict[int, MigrationFn],
) -> dict:
    """Apply sequential migrations from the document's current version to *target_version*.

    Parameters
    ----------
    document:
        A Cosmos DB document dict.  Must contain a ``schemaVersion`` key
        (defaults to ``1`` if missing).
    target_version:
        The schema version the document should be migrated to.
    migrations:
        Mapping from *source* version to a callable that accepts a document
        dict and returns the migrated document dict.  Each function **must**
        set ``schemaVersion`` to ``source + 1``.

    Returns
    -------
    dict
        The migrated document.  If the document is already at
        *target_version* the original dict is returned unchanged.

    Raises
    ------
    ValueError
        If a required migration function is missing from *migrations*.
    """
    current = document.get("schemaVersion", 1)

    if current >= target_version:
        return document

    doc = dict(document)  # shallow copy to avoid mutating the original

    while current < target_version:
        fn = migrations.get(current)
        if fn is None:
            msg = f"No migration registered for schemaVersion {current} → {current + 1}"
            raise ValueError(msg)
        logger.debug("Migrating document %s from v%d to v%d", doc.get("id", "?"), current, current + 1)
        doc = fn(doc)
        current = doc.get("schemaVersion", current + 1)

    return doc
