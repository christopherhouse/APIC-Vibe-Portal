# Schema Versioning

## Overview

This document defines the schema versioning and migration strategy for all Cosmos DB documents in the APIC Vibe Portal. Because Cosmos DB is schema-less, schema evolution is managed at the application layer using a `schemaVersion` field on every document and a lazy migration pattern.

## Schema Version Field

Every document in every container includes a `schemaVersion` integer field:

```json
{
  "schemaVersion": 1,
  "id": "...",
  ...
}
```

- The version starts at `1` and increments for each breaking schema change.
- Non-breaking additions (new optional fields) do not require a version increment.
- Breaking changes (renamed fields, type changes, removed fields) require a version increment.

## Lazy Migration Pattern

Rather than bulk-migrating all documents when a schema changes, the portal uses **lazy migration**:

1. **Read**: When a document is read, check its `schemaVersion`.
2. **Transform**: If the version is older than the current version, apply migration functions to transform it to the current schema.
3. **Write-back**: On the next update of the document, write it back with the new schema version.

This avoids expensive bulk migrations and distributes the migration cost over normal read/write operations.

### Example: Chat Session Migration (v1 → v2)

```python
# v1 schema: id, userId, title, messages, createdAt, updatedAt
# v2 schema: adds model (str) and tokensUsed (int)

def migrate_chat_session(doc: dict) -> dict:
    version = doc.get("schemaVersion", 1)
    if version < 2:
        doc["model"] = "gpt-4"
        doc["tokensUsed"] = 0
        doc["schemaVersion"] = 2
    return doc
```

### Migration Registry

Each repository maintains a list of migration functions keyed by source version:

```python
MIGRATIONS = {
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
}
```

The lazy migration utility applies migrations sequentially from the document's current version to the target version.

## Breaking vs Non-Breaking Changes

| Change Type         | Example                        | Version Increment? | Migration Needed? |
| ------------------- | ------------------------------ | ------------------ | ----------------- |
| Add optional field  | Add `model?: string`           | No                 | No                |
| Add required field  | Add `tokensUsed: number`       | Yes                | Yes (set default) |
| Rename field        | `created` → `createdAt`        | Yes                | Yes (rename)      |
| Change field type   | `score: string` → `score: int` | Yes                | Yes (convert)     |
| Remove field        | Remove `legacyField`           | Yes                | Yes (strip)       |
| Structural refactor | Flatten nested object          | Yes                | Yes (transform)   |

## Guidelines

1. **Document every migration** in CHANGELOG and in the migration registry code.
2. **Support reading at least N-1 versions** — never drop support for the immediately previous version without a bulk migration.
3. **Test migrations** with unit tests that verify transform correctness for each version pair.
4. **Bulk migration scripts** are reserved for emergency or one-time refactors and should be placed in `scripts/migrations/`.

## Related Documentation

- [Storage Strategy](./storage-strategy.md) — Storage decisions by data class
- [Cosmos DB Indexing](./cosmos-db-indexing.md) — Partitioning, indexing, and query patterns
