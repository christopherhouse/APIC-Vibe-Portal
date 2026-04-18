# Cosmos DB Indexing Strategy

## Overview

This document defines the partitioning, indexing, and query optimization strategies for all Cosmos DB containers in the APIC Vibe Portal. The goal is to minimize Request Unit (RU) consumption while supporting the portal's primary query patterns.

## Partitioning Strategy

| Container              | Partition Key | Rationale                                                             |
| ---------------------- | ------------- | --------------------------------------------------------------------- |
| `chat-sessions`        | `/userId`     | Co-locates all sessions for a user; single-user queries are efficient |
| `governance-snapshots` | `/apiId`      | Co-locates all snapshots for an API; supports API-level queries       |
| `analytics-events`     | `/eventType`  | Groups events by type for efficient aggregation queries               |

## Indexing Policies

### chat-sessions

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{ "path": "/*" }],
  "excludedPaths": [{ "path": "/messages/*" }],
  "compositeIndexes": [
    [
      { "path": "/userId", "order": "ascending" },
      { "path": "/createdAt", "order": "descending" }
    ]
  ]
}
```

**Rationale**: Exclude `messages` array from indexing (large text, not queried directly). Composite index on `(userId, createdAt)` supports the primary query: "list a user's sessions, newest first."

### governance-snapshots

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{ "path": "/*" }],
  "excludedPaths": [{ "path": "/findings/*" }],
  "compositeIndexes": [
    [
      { "path": "/apiId", "order": "ascending" },
      { "path": "/timestamp", "order": "descending" }
    ]
  ]
}
```

**Rationale**: Exclude `findings` array from indexing (large structured data, queried only after document retrieval). Composite index on `(apiId, timestamp)` supports "list an API's snapshots, newest first."

### analytics-events

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{ "path": "/*" }],
  "excludedPaths": [{ "path": "/metadata/*" }],
  "compositeIndexes": [
    [
      { "path": "/eventType", "order": "ascending" },
      { "path": "/timestamp", "order": "descending" }
    ]
  ]
}
```

**Rationale**: Exclude `metadata` from indexing (variable-structure payload). Composite index on `(eventType, timestamp)` supports "list events of a given type, newest first."

## Query Optimization Guidelines

1. **Always include the partition key** in queries to avoid cross-partition scans.
2. **Use point reads** (`read_item` by ID + partition key) instead of queries wherever possible — point reads cost 1 RU for a 1 KB document.
3. **Limit result sets** using `max_item_count` and pagination with continuation tokens.
4. **Project only needed fields** using `SELECT c.id, c.title, c.createdAt FROM c` instead of `SELECT * FROM c` for list queries.
5. **Monitor RU consumption** via Application Insights and Cosmos DB diagnostics to identify and optimize hot queries.

## Related Documentation

- [Storage Strategy](./storage-strategy.md) — Storage decisions by data class
- [Schema Versioning](./schema-versioning.md) — Schema evolution and migration
