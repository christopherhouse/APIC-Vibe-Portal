# PII Handling

## Overview

This document identifies Personally Identifiable Information (PII) fields across all data classes and defines handling guidelines for logging, storage, and deletion. The APIC Vibe Portal follows a principle of minimal PII collection and provides mechanisms for GDPR-compliant data erasure.

## PII Fields by Data Class

### Chat Sessions

| Field                | PII Type      | Handling                                                       |
| -------------------- | ------------- | -------------------------------------------------------------- |
| `userId`             | Direct PII    | Required for data ownership; included in partition key         |
| `messages[].content` | Potential PII | User queries may contain PII; stored as-is for session context |

### Governance Snapshots

| Field     | PII Type | Handling                                        |
| --------- | -------- | ----------------------------------------------- |
| `agentId` | Indirect | System-generated agent identifier; not user PII |

### Analytics Telemetry

| Field            | PII Type      | Handling                                                      |
| ---------------- | ------------- | ------------------------------------------------------------- |
| `userId`         | Direct PII    | Hash before storage where possible                            |
| `metadata.query` | Potential PII | User search queries may contain PII; sanitize sensitive terms |

## PII Handling Rules

### Storage

1. **Minimize PII**: Only collect PII fields that are necessary for the feature to function.
2. **Hash Where Possible**: For analytics, hash user IDs (`userId`) before storage so trends can be analyzed without exposing individual identity.
3. **No PII in Partition Keys (Analytics)**: The analytics container uses `eventType` as its partition key, not user identifiers.

### Logging

1. **Never log PII**: Do not include `userId`, email addresses, IP addresses, or user query text in application logs.
2. **Mask in Structured Logs**: If a log context includes a user identifier, replace it with a masked value (e.g., `user:***`).
3. **Exception**: Audit logs for GDPR deletion requests may log the `userId` of the requesting user for compliance traceability.

### Deletion

1. **Right to Erasure**: Support GDPR-compliant deletion of all user data upon request (see [Data Retention Policy](./data-retention-policy.md)).
2. **Cascading Delete**: When a user is deleted, remove records from all containers where `userId` matches.
3. **Audit Trail**: Log the deletion event (timestamp, requesting principal) without logging the deleted data content.

## Related Documentation

- [Storage Strategy](./storage-strategy.md) — Storage decisions by data class
- [Data Retention Policy](./data-retention-policy.md) — Retention periods and deletion methods
