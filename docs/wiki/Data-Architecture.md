# Data Architecture

## Overview

All persistent data is stored in **Azure Cosmos DB** (NoSQL API, serverless capacity mode). Serverless eliminates the need to manage throughput and scales automatically with the portal's variable-traffic pattern.

## Cosmos DB Database

- **Database name**: `apic-vibe-portal`
- **Capacity mode**: Serverless (pay-per-request)
- **API**: NoSQL (SQL API)

## Data Classes

### Chat Sessions (`chat-sessions`)

| Property | Value |
|----------|-------|
| Container | `chat-sessions` |
| Partition key | `/userId` |
| Rationale | High write throughput, flexible schema, natural partitioning by user |

**Schema fields**: session ID, user ID, title, messages array, created timestamp, updated timestamp, model name, tokens used, schema version, soft-delete flags.

### Governance Snapshots (`governance-snapshots`)

| Property | Value |
|----------|-------|
| Container | `governance-snapshots` |
| Partition key | `/apiId` |
| Rationale | Structured compliance data, point-in-time queries, relationship to APIs |

**Schema fields**: snapshot ID, API ID, timestamp, findings array, compliance score, agent ID, schema version, soft-delete flags.

### Analytics Events (`analytics-events`)

| Property | Value |
|----------|-------|
| Container | `analytics-events` |
| Partition key | `/eventType` |
| Rationale | High-volume writes, time-series queries, eventual archival to cold storage |

**Schema fields**: event ID, event type, timestamp, user ID, API ID, metadata object, schema version, soft-delete flags.

## Design Decisions

1. **Single database**: All containers in one `apic-vibe-portal` database
2. **Serverless capacity**: Pay-per-request, auto-scaling
3. **Cosmos DB for all persistence**: No separate relational DB or blob storage needed at this stage
4. **Schema versioning**: Every document has a `schemaVersion` field for forward-compatible reads and lazy migration
5. **Soft delete**: All data classes support `isDeleted` + `deletedAt` before permanent purge

## Data Retention Policy

| Data Class | Active Retention | Deletion Method |
|------------|-----------------|-----------------|
| Chat sessions | 1 year from last activity | Soft delete then purge via TTL |
| Governance snapshots | 3 years | Soft delete then purge via TTL |
| Analytics events | 90 days (hot), 1 year (archive) | TTL + cold storage archival |

GDPR erasure requests trigger immediate soft delete + scheduled purge within 30 days.

## PII Handling

### PII Fields

| Container | PII Field | Handling |
|-----------|-----------|---------|
| `chat-sessions` | `userId` | Pseudonymized (Entra OID, not email) |
| `chat-sessions` | `messages[].content` | May contain PII — not indexed, not logged |
| `analytics-events` | `userId` | Pseudonymized (Entra OID) |
| `governance-snapshots` | — | No direct PII |

### Rules

- **Never log PII** — log `userId` (OID) only, not email or display name
- **Prompt sanitization** — AI prompts are inspected and PII is masked before logging
- **No PII in search indexes** — AI Search indexes contain API metadata only
- **Data minimization** — collect only what is needed for the feature

## Schema Versioning

All documents include:

```json
{
  "schemaVersion": 1,
  "id": "...",
  ...
}
```

**Migration strategy**: Lazy migration on read. When the BFF reads a document with an older `schemaVersion`, it applies the migration in-memory and writes the upgraded document back. No batch migrations needed.

## Cosmos DB Indexing

Default Cosmos DB indexing is used with the following customizations:

| Container | Custom Index | Purpose |
|-----------|-------------|---------|
| `chat-sessions` | Composite index on (`userId`, `updatedAt`) | Efficient user session listing |
| `governance-snapshots` | Index on `apiId` + `timestamp` | Point-in-time governance queries |
| `analytics-events` | Index on `eventType` + `timestamp` | Time-series event queries |

High-write containers use **lazy indexing** where appropriate to improve write throughput.

## Related Documentation

- `docs/architecture/storage-strategy.md` — Full storage strategy document
- `docs/architecture/data-retention-policy.md` — Detailed retention and deletion rules
- `docs/architecture/pii-handling.md` — PII field inventory and handling guidelines
- `docs/architecture/cosmos-db-indexing.md` — Indexing policies and query patterns
- `docs/architecture/schema-versioning.md` — Schema evolution and lazy migration

## Related Wiki Pages

- [[Architecture]] — Overall system architecture
- [[Security]] — Data classification and encryption
- [[Caching]] — Redis cache strategy
