# Data Retention Policy

## Overview

This document defines retention periods, deletion methods, and lifecycle management for all persistent data in the APIC Vibe Portal. Data retention is handled by **Cosmos DB native TTL** (Time-to-Live): when a document is soft-deleted, a `ttl` field is set on the document and Cosmos DB automatically purges it after the configured period.

## Retention Schedule

| Data Class           | Retention Period | Rationale                         | Deletion Method                                          |
| -------------------- | ---------------- | --------------------------------- | -------------------------------------------------------- |
| Chat sessions        | 90 days          | Privacy, compliance               | Soft delete sets `ttl`; Cosmos DB auto-purges after 90d  |
| Governance snapshots | 2 years          | Audit, compliance                 | Soft delete sets `ttl`; Cosmos DB auto-purges after 730d |
| Analytics telemetry  | 1 year           | Trend analysis, cost optimization | Soft delete sets `ttl`; Cosmos DB auto-purges after 365d |

## Soft Delete with Cosmos DB TTL

All records support a two-phase deletion model powered by Cosmos DB native TTL:

1. **Soft Delete**: Mark the record with `isDeleted: true`, `deletedAt: <timestamp>`, and `ttl: <seconds>`. Soft-deleted records are excluded from normal queries but remain in the database until the TTL expires.
2. **Automatic Purge**: Cosmos DB automatically and permanently removes the document once the `ttl` elapses. No custom cleanup job is required.

### How It Works

Each container has `defaultTtl: -1` in its Bicep definition, which enables per-document TTL without a container-wide default. Documents without a `ttl` field live indefinitely. When `soft_delete()` is called, the repository sets:

```json
{
  "isDeleted": true,
  "deletedAt": "2026-04-18T12:00:00Z",
  "ttl": 7776000
}
```

The `ttl` value (in seconds) varies by container:

| Container              | TTL (seconds) | Equivalent |
| ---------------------- | ------------- | ---------- |
| `chat-sessions`        | 7,776,000     | 90 days    |
| `governance-snapshots` | 63,072,000    | 730 days   |
| `analytics-events`     | 31,536,000    | 365 days   |

### Soft Delete Fields

Every document schema includes:

```json
{
  "isDeleted": false,
  "deletedAt": null
}
```

When soft-deleted, the `ttl` field is added and Cosmos DB handles the rest.

## User Data Deletion (GDPR Right to Erasure)

When a user requests deletion of their data:

1. Query all containers for records belonging to the user (`userId` field).
2. Hard-delete (permanently remove) all matching records immediately.
3. Log the deletion request and outcome for audit purposes (without logging the deleted data content).

## Related Documentation

- [Storage Strategy](./storage-strategy.md) — Storage decisions by data class
- [PII Handling](./pii-handling.md) — PII identification and redaction rules
