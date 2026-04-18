# Data Retention Policy

## Overview

This document defines retention periods, deletion methods, and lifecycle management for all persistent data in the APIC Vibe Portal. All data has a defined retention period after which it is purged according to the method specified below.

## Retention Schedule

| Data Class           | Retention Period         | Rationale                         | Deletion Method                         |
| -------------------- | ------------------------ | --------------------------------- | --------------------------------------- |
| Chat sessions        | 90 days                  | Privacy, compliance               | Soft delete, then purge via cleanup job |
| Governance snapshots | 2 years                  | Audit, compliance                 | Soft delete, then purge via cleanup job |
| Analytics telemetry  | 1 year hot, 3 years cold | Trend analysis, cost optimization | Soft delete, then purge via cleanup job |

## Soft Delete

All records support a two-phase deletion model:

1. **Soft Delete**: Mark the record with `isDeleted: true` and `deletedAt: <timestamp>`. Soft-deleted records are excluded from normal queries but remain in the database.
2. **Hard Delete**: A scheduled data-retention cleanup job permanently removes soft-deleted records after the retention period has elapsed.

### Soft Delete Fields

Every document schema includes:

```json
{
  "isDeleted": false,
  "deletedAt": null
}
```

## Data Retention Cleanup Job

A scheduled job runs periodically to hard-delete records that have exceeded their retention period.

- **Job Location**: `src/bff/apic_vibe_portal_bff/jobs/data_retention_job.py`
- **Frequency**: Daily (recommended via Azure Container Apps Job or external scheduler)
- **Logic**: For each container, query soft-deleted documents where `deletedAt` is older than the retention period, then permanently delete them.

### Cleanup Thresholds

| Container              | Purge Condition                               |
| ---------------------- | --------------------------------------------- |
| `chat-sessions`        | `isDeleted == true AND deletedAt < now - 90d` |
| `governance-snapshots` | `isDeleted == true AND deletedAt < now - 2y`  |
| `analytics-events`     | `isDeleted == true AND deletedAt < now - 1y`  |

## User Data Deletion (GDPR Right to Erasure)

When a user requests deletion of their data:

1. Query all containers for records belonging to the user (`userId` field).
2. Hard-delete (permanently remove) all matching records immediately.
3. Log the deletion request and outcome for audit purposes (without logging the deleted data content).

## Related Documentation

- [Storage Strategy](./storage-strategy.md) — Storage decisions by data class
- [PII Handling](./pii-handling.md) — PII identification and redaction rules
