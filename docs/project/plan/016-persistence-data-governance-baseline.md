# 016 - Phase 1 MVP: Persistence & Data Governance Baseline

> **🔲 Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References
- [Architecture Document](../apic_architecture.md) — Data architecture, storage strategy, Cosmos DB
- [Product Charter](../apic_product_charter.md) — Data governance, compliance, retention policies
- [Product Spec](../apic_portal_spec.md) — Data persistence requirements

## Overview
Establish the persistence and data governance baseline before implementing features that depend on storing chat history, governance snapshots, or analytics telemetry. This includes storage strategy, retention policies, schema management, and query optimization for trend workloads.

## Dependencies
- **002** — Azure infrastructure (Cosmos DB, Storage Account)
- **005** — BFF API setup (data layer integration points)
- **006** — Shared types package (data models)
- **008** — Entra ID authentication (user identity for data ownership)
- **011** — AI Search index (search data persistence)
- **014** — Search API (historical query storage)

## Implementation Details

### 1. Storage Strategy by Data Class
Define and document storage choices for each data class:

**Chat Session Data**
- **Storage**: Azure Cosmos DB (NoSQL)
- **Container**: `chat-sessions`
- **Partition Key**: `/userId`
- **Rationale**: High write throughput, flexible schema, global distribution, natural partitioning by user
- **Schema**: Session ID, user ID, messages[], created, updated, metadata (model, tokens used)

**Governance Snapshots**
- **Storage**: Azure Cosmos DB (NoSQL)
- **Container**: `governance-snapshots`
- **Partition Key**: `/apiId`
- **Rationale**: Structured compliance data, point-in-time queries, relationship to APIs
- **Schema**: Snapshot ID, API ID, timestamp, findings[], compliance score, agent ID

**Analytics Telemetry**
- **Storage**: Azure Cosmos DB (NoSQL) or Azure Storage (hot/cool tiers)
- **Container**: `analytics-events`
- **Partition Key**: `/eventType` or `/date` (e.g., `/2026-04-14`)
- **Rationale**: High-volume writes, time-series queries, eventual archival to cold storage
- **Schema**: Event ID, event type, timestamp, user ID, API ID, metadata (query, duration, result count)

**Large Artifacts (SBOM, reports)**
- **Storage**: Azure Blob Storage
- **Container**: `artifacts`
- **Rationale**: Cost-effective for large files, versioning support, immutable storage
- **Schema**: Blob name = `{apiId}/{artifactType}/{version}/{filename}`

Document storage decisions:
```
docs/architecture/
└── storage-strategy.md
```

### 2. Retention & Deletion Policy
Define retention policies for each data class:

| Data Class | Retention Period | Rationale | Deletion Method |
|------------|------------------|-----------|-----------------|
| Chat sessions | 90 days | Privacy, compliance | Soft delete, then purge via TTL |
| Governance snapshots | 2 years | Audit, compliance | Archive to cold storage, then purge |
| Analytics telemetry | 1 year hot, 3 years cold | Trend analysis, cost optimization | Auto-tier to cool/archive, then purge |
| Large artifacts | Indefinite (versioned) | Compliance, traceability | Manual deletion only |

**PII Handling**
- Identify PII fields (user ID, email, IP address, query text)
- Mask or redact PII in logs
- Support user data deletion requests (GDPR right to erasure)
- Document PII fields and handling in `docs/architecture/pii-handling.md`

**Soft Delete Implementation**
- Add `isDeleted` flag and `deletedAt` timestamp to schemas
- Filter out soft-deleted records in queries
- Implement hard delete via scheduled job (Azure Function) that purges soft-deleted records after retention period

```
infra/functions/
└── data-retention-cleanup.bicep   # Azure Function for retention enforcement

src/bff/src/jobs/
├── data-retention-job.ts          # Job logic
└── data-retention-job.test.ts
```

### 3. Partition, Index & Query Strategy
**Cosmos DB Partitioning**
- Chat sessions: Partition by `/userId` (ensures single-user queries are efficient, co-locates user data)
- Governance snapshots: Partition by `/apiId` (co-locates all snapshots for an API, supports API-level queries)
- Analytics events: Partition by `/date` (time-series queries, easy archival of old partitions)

**Indexing Strategy**
- Default indexing policy: Index all fields (Cosmos DB default)
- Exclude large text fields from indexing (chat message content, compliance findings)
- Create composite indexes for common queries:
  - Chat sessions: `(userId, createdAt)` descending
  - Governance snapshots: `(apiId, timestamp)` descending
  - Analytics events: `(eventType, timestamp)` descending

**Query Optimization**
- Use partition key in all queries where possible
- Limit result sets (pagination with continuation tokens)
- Use point reads (by ID) instead of queries where possible
- Monitor RU consumption and optimize hot queries

Document indexing and query patterns:
```
docs/architecture/
└── cosmos-db-indexing.md
```

### 4. Schema Ownership, Versioning & Migration
**Schema Ownership**
- Define TypeScript interfaces in `src/shared/types/data-models.ts`
- Use Zod or Joi for runtime validation
- Document breaking changes in CHANGELOG

**Schema Versioning**
- Add `schemaVersion` field to all documents
- Increment version on breaking changes
- Support backward-compatible reads (read v1 and v2, write v2)

**Migration Strategy**
- No automatic migrations (Cosmos DB is schema-less)
- Implement lazy migration: Read old schema, transform to new schema, write new schema on next update
- For breaking changes requiring bulk migration, create one-time migration script (Azure Function or script in `scripts/migrations/`)

**Example: Chat Session Schema Evolution**
```typescript
// v1 (initial)
interface ChatSessionV1 {
  schemaVersion: 1;
  id: string;
  userId: string;
  messages: Message[];
  created: string;
  updated: string;
}

// v2 (add model and token tracking)
interface ChatSessionV2 {
  schemaVersion: 2;
  id: string;
  userId: string;
  messages: Message[];
  created: string;
  updated: string;
  model?: string;         // New field
  tokensUsed?: number;    // New field
}

// Migration function
function migrateChatSession(session: ChatSessionV1 | ChatSessionV2): ChatSessionV2 {
  if (session.schemaVersion === 1) {
    return { ...session, schemaVersion: 2, model: 'gpt-4', tokensUsed: 0 };
  }
  return session;
}
```

Document migration approach:
```
docs/architecture/
└── schema-versioning.md
```

### 5. Data Access Layer (BFF)
Create a data access layer in the BFF:
```
src/bff/src/data/
├── cosmos-client.ts               # Cosmos DB client initialization
├── repositories/
│   ├── chat-session.repository.ts
│   ├── governance.repository.ts
│   └── analytics.repository.ts
├── models/
│   ├── chat-session.model.ts      # Re-export from shared types
│   ├── governance.model.ts
│   └── analytics.model.ts
└── migrations/
    └── lazy-migration.util.ts     # Lazy migration utility
```

**Repository Pattern**
- Abstract Cosmos DB queries behind repositories
- Implement CRUD operations: `create`, `findById`, `findByPartitionKey`, `update`, `delete` (soft delete)
- Handle pagination with continuation tokens
- Handle schema migrations transparently

**Configuration**
BFF environment variables:
- `COSMOS_DB_ENDPOINT`
- `COSMOS_DB_KEY` (or use Managed Identity)
- `COSMOS_DB_DATABASE_NAME`
- `COSMOS_DB_CHAT_CONTAINER`
- `COSMOS_DB_GOVERNANCE_CONTAINER`
- `COSMOS_DB_ANALYTICS_CONTAINER`

### 6. Data Governance Documentation
Create comprehensive data governance documentation:
```
docs/architecture/
├── storage-strategy.md            # Storage decisions by data class
├── pii-handling.md                # PII identification and handling
├── data-retention-policy.md       # Retention periods and deletion
├── cosmos-db-indexing.md          # Partitioning, indexing, query patterns
└── schema-versioning.md           # Schema evolution and migration
```

## Testing & Acceptance Criteria
- [ ] Storage strategy document exists and covers all data classes
- [ ] Data retention policy document exists with clear retention periods
- [ ] PII handling document identifies PII fields and redaction rules
- [ ] Cosmos DB indexing strategy document exists
- [ ] Schema versioning document exists with migration examples
- [ ] Cosmos DB containers are provisioned in infrastructure with correct partition keys
- [ ] Repository classes implement CRUD operations with unit tests
- [ ] Soft delete is implemented and tested
- [ ] Data retention job is implemented and can purge old data
- [ ] Schema migration utility is implemented and tested
- [ ] Pagination is implemented and tested
- [ ] All repositories have unit tests with >80% coverage
- [ ] Integration tests verify Cosmos DB queries work as expected

## Implementation Notes
<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History
| Date | Status | Author | Notes |
|------|--------|--------|-------|
| — | 🔲 Not Started | — | Task created |

### Technical Decisions
_No technical decisions recorded yet._

### Deviations from Plan
_No deviations from the original plan._

### Validation Results
_No validation results yet._


## Coding Agent Prompt

```text
**Task**: Implement plan step 016 — Persistence & Data Governance Baseline.

Read the full task specification at `docs/project/plan/016-persistence-data-governance-baseline.md`.

Reference the architecture at `docs/project/apic_architecture.md` (Data Architecture section), the infrastructure setup in `docs/project/plan/002-sprint-zero-azure-infra-bicep.md`, and the shared types in `docs/project/plan/006-shared-types-package.md`.

Define and document storage strategy for chat sessions, governance snapshots, analytics telemetry, and large artifacts. Create data retention and deletion policies with PII handling guidelines. Design Cosmos DB partitioning and indexing strategies. Implement schema versioning and lazy migration. Create repository pattern data access layer in the BFF with CRUD operations, soft delete, and pagination. Implement data retention cleanup job.

Write comprehensive unit and integration tests for all repositories and data access code. Verify Cosmos DB queries are optimized and follow best practices.

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/016-persistence-data-governance-baseline.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
