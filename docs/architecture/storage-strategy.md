# Storage Strategy

## Overview

This document defines the storage strategy for all persistent data in the APIC Vibe Portal. All persistent data is stored in **Azure Cosmos DB** using the NoSQL (SQL) API with **serverless capacity mode** (pay-per-request, no provisioned throughput) to optimize for the portal's variable-traffic pattern.

## Data Classes

### 1. Chat Session Data

| Property          | Value                                                                |
| ----------------- | -------------------------------------------------------------------- |
| **Storage**       | Azure Cosmos DB (NoSQL, serverless)                                  |
| **Container**     | `chat-sessions`                                                      |
| **Partition Key** | `/userId`                                                            |
| **Rationale**     | High write throughput, flexible schema, natural partitioning by user |

**Schema Fields**: Session ID, user ID, title, messages array, created timestamp, updated timestamp, model name, tokens used, schema version, soft-delete flags.

### 2. Governance Snapshots

| Property          | Value                                                                   |
| ----------------- | ----------------------------------------------------------------------- |
| **Storage**       | Azure Cosmos DB (NoSQL, serverless)                                     |
| **Container**     | `governance-snapshots`                                                  |
| **Partition Key** | `/apiId`                                                                |
| **Rationale**     | Structured compliance data, point-in-time queries, relationship to APIs |

**Schema Fields**: Snapshot ID, API ID, timestamp, findings array, compliance score, agent ID, schema version, soft-delete flags.

### 3. Analytics Telemetry

| Property          | Value                                                                      |
| ----------------- | -------------------------------------------------------------------------- |
| **Storage**       | Azure Cosmos DB (NoSQL, serverless)                                        |
| **Container**     | `analytics-events`                                                         |
| **Partition Key** | `/eventType`                                                               |
| **Rationale**     | High-volume writes, time-series queries, eventual archival to cold storage |

**Schema Fields**: Event ID, event type, timestamp, user ID, API ID, metadata object, schema version, soft-delete flags.

## Design Decisions

1. **Single Database**: All containers live within the `apic-vibe-portal` database in Cosmos DB.
2. **Serverless Capacity**: Pay-per-request model eliminates the need to manage throughput and scales automatically.
3. **Cosmos DB for All Persistence**: Cosmos DB covers all persistence needs. Large artifact storage (SBOMs, reports) is deferred — if a need materializes, Azure Blob Storage can be added later.
4. **Schema Versioning**: Every document includes a `schemaVersion` field to support forward-compatible reads and lazy migration.
5. **Soft Delete**: All data classes support soft delete via `isDeleted` and `deletedAt` fields before permanent purge.

## Related Documentation

- [Data Retention Policy](./data-retention-policy.md) — Retention periods and deletion methods
- [PII Handling](./pii-handling.md) — PII field identification and handling guidelines
- [Cosmos DB Indexing](./cosmos-db-indexing.md) — Partitioning, indexing, and query patterns
- [Schema Versioning](./schema-versioning.md) — Schema evolution and lazy migration
- [Architecture Document](../project/apic_architecture.md) — Overall system architecture
