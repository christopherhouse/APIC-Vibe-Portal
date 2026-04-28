# Task 034 — Azure API Center Backup

> 🔲 **Status: Not Started**
>
> _This is a living document. Status and implementation notes are updated as work progresses._

## References

- [Architecture Document](../apic_architecture.md) — Components, security, deployment, data architecture
- [Product Charter](../apic_product_charter.md) — Operational resilience, backup & restore goals
- [Product Spec](../apic_portal_spec.md) — Backup feature specification
- [Persistence & Data Governance Baseline](016-persistence-data-governance-baseline.md) — Cosmos DB patterns, repository pattern
- [Azure Infrastructure as Code](002-sprint-zero-azure-infra-bicep.md) — Bicep module conventions, managed identity patterns
- [Entra ID Authentication](008-entra-id-authentication.md) — Auth integration, RBAC roles

## Overview

Implement a fully automated Azure API Center backup system that captures the complete state of an API Center resource — all APIs, versions, definitions, deployments, environments, and their associated metadata/specs — into a self-contained ZIP archive stored in Azure Blob Storage. The backup must contain everything needed to completely rehydrate a new API Center instance from scratch (restore capability will be built in a future task).

Backups run on an hourly cron schedule via an Azure Container Apps Job. A configurable retention policy (hourly/daily/monthly/annual) governs how many backups are kept. An admin-only "Backup" section in the portal UI allows users to browse backup history with metadata about each backup (timestamp, size, API/entity counts).

## Dependencies

- **002** — Azure Infrastructure (Bicep modules, managed identity pattern)
- **006** — BFF API project setup (FastAPI routers, dependency injection)
- **005** — Frontend Next.js setup (MUI components, App Router)
- **008** — Entra ID authentication (RBAC enforcement)
- **009** — API Center Data Layer (API Center SDK client, entity models)
- **016** — Persistence & Data Governance Baseline (Cosmos DB repository pattern)
- **020** — Security Trimming (admin role enforcement)

## Architecture

### High-Level Flow

```
┌──────────────┐   hourly cron   ┌──────────────────────┐
│  Container   │ ───────────────>│  Backup Job          │
│  Apps Env    │                 │  (Python container)  │
└──────────────┘                 └──────┬───────────────┘
                                        │
                   ┌────────────────────┼────────────────────┐
                   │                    │                    │
                   ▼                    ▼                    ▼
          ┌────────────────┐   ┌───────────────┐   ┌───────────────┐
          │ Azure API      │   │ Azure Blob    │   │ Azure         │
          │ Center         │   │ Storage       │   │ Cosmos DB     │
          │ (read APIs,    │   │ (store ZIP    │   │ (backup       │
          │  specs, etc.)  │   │  archives)    │   │  metadata)    │
          └────────────────┘   └───────────────┘   └───────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │ Portal UI    │
                                 │ (admin-only  │
                                 │  browse)     │
                                 └──────────────┘
```

### Backup ZIP Structure

```
apic-backup-2026-04-28T12-00-00Z.zip
├── manifest.json                    # Backup metadata (version, timestamp, counts, source)
├── environments/
│   ├── env-1.json                   # Environment definition
│   └── env-2.json
├── apis/
│   ├── api-1/
│   │   ├── api.json                 # API metadata (title, description, kind, contacts, etc.)
│   │   ├── versions/
│   │   │   ├── v1/
│   │   │   │   ├── version.json     # Version metadata
│   │   │   │   └── definitions/
│   │   │   │       ├── def-1/
│   │   │   │       │   ├── definition.json   # Definition metadata
│   │   │   │       │   └── spec.json|yaml    # Raw specification content
│   │   │   │       └── def-2/
│   │   │   │           ├── definition.json
│   │   │   │           └── spec.yaml
│   │   │   └── v2/
│   │   │       └── ...
│   │   └── deployments/
│   │       ├── deployment-1.json    # Deployment definition
│   │       └── deployment-2.json
│   └── api-2/
│       └── ...
└── metadata/
    └── custom-metadata-schemas.json  # Custom metadata schema definitions
```

### Manifest Schema

```json
{
  "version": "1.0",
  "format": "apic-backup",
  "createdAt": "2026-04-28T12:00:00Z",
  "source": {
    "subscriptionId": "...",
    "resourceGroup": "...",
    "serviceName": "...",
    "location": "eastus2"
  },
  "counts": {
    "apis": 42,
    "versions": 87,
    "definitions": 103,
    "deployments": 56,
    "environments": 3
  },
  "backupJobVersion": "1.0.0"
}
```

## Implementation Details

### 1. Infrastructure — Bicep Module

```
infra/modules/
├── backup-storage.bicep        # Storage account + blob container for backups
```

Create a dedicated storage account (or a blob container in the existing `function-storage` account if appropriate) with:

- **Container**: `apic-backups` (private access)
- **Lifecycle management policy**: Automatic tier transitions
  - Move to Cool tier after 30 days
  - Move to Archive tier after 90 days
- **Soft delete**: Enabled (14 days retention)
- **Versioning**: Disabled (retention is managed by the backup job, not blob versioning)

Add a new **user-assigned managed identity** for the backup job:

- `{prefix}-id-backup-{env}-{suffix}`
- RBAC roles:
  - `Storage Blob Data Contributor` on the backup storage account
  - `Azure API Center Data Reader` on the API Center resource
  - `Cosmos DB Built-in Data Contributor` on the Cosmos DB account (for backup metadata writes)
  - `AcrPull` on ACR (for container image pull)

Update `infra/main.bicep` to include the new module and identity.

### 2. Backup Job — Container Apps Job

```
src/backup-job/
├── Dockerfile
├── pyproject.toml               # UV-managed Python project
├── uv.lock
├── README.md
└── apic_backup/
    ├── __init__.py
    ├── main.py                  # Entry point — orchestrates full backup
    ├── config.py                # Configuration from environment variables
    ├── clients/
    │   ├── __init__.py
    │   ├── apic_client.py       # Azure API Center SDK client (read all entities)
    │   └── storage_client.py    # Azure Blob Storage client (upload ZIP)
    ├── services/
    │   ├── __init__.py
    │   ├── backup_service.py    # Core backup logic (enumerate → serialize → ZIP → upload)
    │   ├── retention_service.py # Retention policy enforcement (prune old backups)
    │   └── metadata_service.py  # Cosmos DB backup metadata CRUD
    ├── models/
    │   ├── __init__.py
    │   ├── backup_manifest.py   # Manifest Pydantic model
    │   └── backup_metadata.py   # Cosmos DB metadata Pydantic model
    └── tests/
        ├── __init__.py
        ├── test_backup_service.py
        ├── test_retention_service.py
        ├── test_metadata_service.py
        └── conftest.py
```

#### Configuration (Environment Variables)

| Variable | Description | Default |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | Managed identity client ID | — |
| `APIC_SUBSCRIPTION_ID` | API Center subscription ID | — |
| `APIC_RESOURCE_GROUP` | API Center resource group | — |
| `APIC_SERVICE_NAME` | API Center service name | — |
| `BACKUP_STORAGE_ACCOUNT_URL` | Blob storage account URL | — |
| `BACKUP_CONTAINER_NAME` | Blob container name | `apic-backups` |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint | — |
| `COSMOS_DATABASE` | Cosmos DB database name | — |
| `RETENTION_HOURLY` | Number of hourly backups to retain | `24` |
| `RETENTION_DAILY` | Number of daily backups to retain | `30` |
| `RETENTION_MONTHLY` | Number of monthly backups to retain | `12` |
| `RETENTION_ANNUAL` | Number of annual backups to retain | `3` |

#### Backup Process

1. **Enumerate** all entities from API Center via the Azure SDK:
   - List all environments
   - List all APIs → for each API:
     - List all versions → for each version:
       - List all definitions → for each definition:
         - Export the specification content
     - List all deployments
   - List custom metadata schemas
2. **Serialize** each entity to JSON (preserving all fields)
3. **Package** into a ZIP archive following the structure above
4. **Generate** the `manifest.json` with entity counts and source metadata
5. **Upload** the ZIP to Azure Blob Storage with blob metadata:
   - `backup-timestamp`: ISO 8601 timestamp
   - `api-count`: number of APIs
   - `entity-count`: total entities (APIs + versions + definitions + deployments + environments)
   - `backup-version`: manifest format version
6. **Write** backup metadata record to Cosmos DB (for fast querying from the UI)
7. **Run retention** — prune backups exceeding the configured retention limits

#### Retention Policy Logic

Retention operates on a grandfather-father-son (GFS) scheme:

- **Hourly**: Keep the last N hourly backups (default 24)
- **Daily**: Keep the last N daily backups — the last backup of each day (default 30)
- **Monthly**: Keep the last N monthly backups — the last backup of each month (default 12)
- **Annual**: Keep the last N annual backups — the last backup of each year (default 3)

A single backup can satisfy multiple retention tiers (e.g., the last backup on Dec 31 counts as hourly, daily, monthly, and annual). Backups that don't fall into any retention tier are deleted (both the blob and the Cosmos DB metadata record).

The retention service:
1. Lists all backup metadata from Cosmos DB (ordered by timestamp descending)
2. Tags each backup with the retention tiers it satisfies
3. Identifies backups that satisfy no tier
4. Deletes orphaned backups (blob + Cosmos DB record)

### 3. Cosmos DB — Backup Metadata Container

Add a new container to the existing Cosmos DB database:

| Property | Value |
| --- | --- |
| Container name | `backup-metadata` |
| Partition key | `/sourceServiceName` |
| Unique key | `/backupId` |

#### Document Schema

```json
{
  "id": "apic-backup-2026-04-28T12-00-00Z",
  "backupId": "apic-backup-2026-04-28T12-00-00Z",
  "sourceServiceName": "apic-prod",
  "timestamp": "2026-04-28T12:00:00Z",
  "blobUrl": "https://storageacct.blob.core.windows.net/apic-backups/apic-backup-2026-04-28T12-00-00Z.zip",
  "blobName": "apic-backup-2026-04-28T12-00-00Z.zip",
  "sizeBytes": 2457600,
  "counts": {
    "apis": 42,
    "versions": 87,
    "definitions": 103,
    "deployments": 56,
    "environments": 3
  },
  "retentionTiers": ["hourly", "daily"],
  "status": "completed",
  "durationMs": 12450,
  "error": null,
  "ttl": -1
}
```

### 4. BFF — Backup Admin Endpoints

```
src/bff/apic_vibe_portal_bff/routers/
├── backup.py                  # Backup admin endpoints (FastAPI router)

src/bff/apic_vibe_portal_bff/services/
├── backup_service.py          # Backup metadata query service

src/bff/tests/
├── test_backup_routes.py      # Route tests
```

All endpoints require the **admin** role (enforced via RBAC middleware).

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/admin/backups` | List backups (paginated, sorted by timestamp desc) |
| `GET` | `/api/admin/backups/{backup_id}` | Get backup details |
| `GET` | `/api/admin/backups/{backup_id}/download` | Generate SAS URL for backup download |

#### `GET /api/admin/backups` Response

```json
{
  "data": [
    {
      "backupId": "apic-backup-2026-04-28T12-00-00Z",
      "timestamp": "2026-04-28T12:00:00Z",
      "sizeBytes": 2457600,
      "sizeFormatted": "2.3 MB",
      "counts": {
        "apis": 42,
        "versions": 87,
        "definitions": 103,
        "deployments": 56,
        "environments": 3
      },
      "retentionTiers": ["hourly", "daily"],
      "status": "completed",
      "durationMs": 12450
    }
  ],
  "pagination": {
    "continuationToken": "...",
    "hasMore": true
  }
}
```

#### `GET /api/admin/backups/{backup_id}/download` Response

```json
{
  "data": {
    "downloadUrl": "https://storageacct.blob.core.windows.net/apic-backups/...?sv=...&sig=...",
    "expiresAt": "2026-04-28T13:00:00Z"
  }
}
```

The download endpoint generates a time-limited SAS URL (1 hour expiry) via the Azure Storage SDK using user delegation key (no storage account keys).

### 5. Frontend — Backup Admin Page

```
src/frontend/app/admin/backup/
├── page.tsx                    # Backup list page (Server Component shell)
├── components/
│   ├── BackupList.tsx          # Client component — backup table with pagination
│   ├── BackupDetailDialog.tsx  # Dialog showing full backup details + download button
│   └── BackupStatusChip.tsx    # Status indicator chip (completed/failed/running)
├── __tests__/
│   ├── BackupList.test.tsx
│   └── BackupDetailDialog.test.tsx

src/frontend/lib/
├── backup-api.ts               # Typed API client wrappers
```

#### UI Requirements

- **Location**: `/admin/backup` — accessible only to users with the admin role
- **Navigation**: Add "Backup" item to the admin sidebar/nav (with a backup icon)
- **Backup List Table** (MUI `DataGrid` or `Table`):
  - Columns: Date/Time, Size, APIs, Total Entities, Retention Tier(s), Status, Actions
  - Default sort: newest first
  - Pagination via continuation token
  - Row click or "View" action opens the detail dialog
- **Backup Detail Dialog** (MUI `Dialog`):
  - Full backup metadata display
  - Download button (fetches SAS URL, opens in new tab)
  - Duration display
  - Entity count breakdown
- **Status Chip**:
  - `completed` → green chip
  - `failed` → red chip with error tooltip
  - `running` → blue chip with pulse animation
- **Empty state**: Friendly message when no backups exist yet

### 6. Container Apps Job Deployment

Update `scripts/deploy-container-apps.sh` to deploy the backup job:

```bash
# Deploy backup job as a scheduled Container Apps Job
az containerapp job create \
  --name "${PREFIX}-backup-job-${ENV}" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_APPS_ENV_ID" \
  --image "${ACR_LOGIN_SERVER}/backup-job:${IMAGE_TAG}" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-identity "$BACKUP_IDENTITY_RESOURCE_ID" \
  --user-assigned "$BACKUP_IDENTITY_RESOURCE_ID" \
  --trigger-type Schedule \
  --cron-expression "0 * * * *" \
  --replica-timeout 1800 \
  --replica-retry-limit 1 \
  --parallelism 1 \
  --replica-completion-count 1 \
  --env-vars \
    "AZURE_CLIENT_ID=$BACKUP_IDENTITY_CLIENT_ID" \
    "APIC_SUBSCRIPTION_ID=$SUBSCRIPTION_ID" \
    "APIC_RESOURCE_GROUP=$RESOURCE_GROUP" \
    "APIC_SERVICE_NAME=$APIC_SERVICE_NAME" \
    "BACKUP_STORAGE_ACCOUNT_URL=https://${BACKUP_STORAGE_ACCOUNT_NAME}.blob.core.windows.net" \
    "BACKUP_CONTAINER_NAME=apic-backups" \
    "COSMOS_ENDPOINT=$COSMOS_ENDPOINT" \
    "COSMOS_DATABASE=$COSMOS_DATABASE" \
    "RETENTION_HOURLY=24" \
    "RETENTION_DAILY=30" \
    "RETENTION_MONTHLY=12" \
    "RETENTION_ANNUAL=3"
```

### 7. CI/CD Updates

Add to `.github/workflows/ci.yml`:

- **Lint & test** step for `src/backup-job/` (ruff check, ruff format, pytest)
- **Docker build** step for `src/backup-job/Dockerfile`
- **Deploy** step to push image to ACR and update the Container Apps Job

## Security Considerations

- **Least privilege**: Backup job identity has read-only access to API Center, write access only to backup storage and backup metadata in Cosmos DB
- **No storage account keys**: All blob access uses managed identity + Entra ID tokens
- **SAS URLs**: Download endpoint generates user-delegation SAS tokens (1 hour TTL), not account-key SAS
- **Admin-only UI**: All backup endpoints are gated behind the admin RBAC role
- **Spec content**: API specifications may contain sensitive information — backup storage should have appropriate network access controls (private endpoint in production)
- **Encryption**: Blob storage uses Microsoft-managed encryption at rest by default

## Testing & Acceptance Criteria

### Backup Job

- [ ] Backup job enumerates all APIs, versions, definitions, deployments, and environments from API Center
- [ ] Backup job exports specification content for all definitions
- [ ] Backup job creates a well-formed ZIP with the documented structure
- [ ] Manifest includes accurate entity counts and source metadata
- [ ] ZIP is uploaded to the correct blob container with appropriate metadata tags
- [ ] Backup metadata is written to Cosmos DB with all required fields
- [ ] Retention service correctly identifies backups to prune based on GFS policy
- [ ] Retention service deletes both blob and Cosmos DB record for pruned backups
- [ ] Backup job handles API Center pagination (large catalogs)
- [ ] Backup job handles partial failures gracefully (logs errors, continues with remaining entities)
- [ ] Backup job completes within the 30-minute replica timeout for catalogs up to 500 APIs

### BFF Endpoints

- [ ] `GET /api/admin/backups` returns paginated backup list sorted by timestamp desc
- [ ] `GET /api/admin/backups/{backup_id}` returns full backup details
- [ ] `GET /api/admin/backups/{backup_id}/download` returns a time-limited SAS download URL
- [ ] All backup endpoints require admin role (401/403 for non-admins)
- [ ] Pagination via continuation token works correctly

### Frontend UI

- [ ] `/admin/backup` page is accessible only to admin users
- [ ] Backup list table displays date/time, size, API count, entity count, retention tiers, status
- [ ] Table sorts by newest first by default
- [ ] Pagination loads additional pages via continuation token
- [ ] Detail dialog shows full backup metadata and download button
- [ ] Download button fetches SAS URL and opens download
- [ ] Status chips display correct colors and states
- [ ] Empty state renders when no backups exist
- [ ] Non-admin users are redirected or see an unauthorized message

### Infrastructure

- [ ] Bicep module creates storage account with backup container
- [ ] Lifecycle management policy moves blobs to Cool (30d) and Archive (90d)
- [ ] Managed identity has correct RBAC roles (Storage Blob Data Contributor, API Center Data Reader, Cosmos DB contributor, AcrPull)
- [ ] Container Apps Job deploys with correct cron schedule (`0 * * * *`)
- [ ] Container Apps Job uses the dedicated managed identity

### E2E Tests

- [ ] Playwright: Admin can navigate to `/admin/backup`
- [ ] Playwright: Backup list table renders with expected columns
- [ ] Playwright: Non-admin users cannot access the backup page
- [ ] Playwright: Detail dialog opens on row click and shows metadata

## Implementation Notes

<!--
  This section is a living record updated by the implementing agent.
  Update status, log decisions, and record validation results as work progresses.
  When complete, change the Status at the top of this document to ✅ Complete.
-->

### Status History

| Date | Status         | Author | Notes        |
| ---- | -------------- | ------ | ------------ |
| —    | 🔲 Not Started | —      | Task created |

### Technical Decisions

_(To be filled during implementation)_

### Deviations from Plan

_(To be filled during implementation)_

### Validation Results

_(To be filled during implementation)_

## Coding Agent Prompt

```text
**Task**: Implement plan step 034 — Azure API Center Backup.

Read the full task specification at `docs/project/plan/034-api-center-backup.md`.

Reference the following for context:
- `docs/project/plan/002-sprint-zero-azure-infra-bicep.md` for Bicep module conventions and managed identity patterns
- `docs/project/plan/009-api-center-data-layer.md` for the API Center SDK client
- `docs/project/plan/016-persistence-data-governance-baseline.md` for Cosmos DB repository patterns
- `src/indexer/` for an example Container Apps Job Python project structure
- `src/governance-worker/` for another example Container Apps Job
- `scripts/deploy-container-apps.sh` for Container Apps deployment patterns

Implement the feature in this order:

1. **Infrastructure**: Create `infra/modules/backup-storage.bicep` for the storage account and blob container. Add backup job managed identity to `infra/main.bicep`. Add the `backup-metadata` container to the Cosmos DB module.

2. **Backup Job**: Create `src/backup-job/` — a UV-managed Python project with the backup service, retention service, metadata service, API Center client, and storage client. Include comprehensive pytest tests.

3. **BFF Endpoints**: Add `GET /api/admin/backups`, `GET /api/admin/backups/{backup_id}`, and `GET /api/admin/backups/{backup_id}/download` endpoints behind admin RBAC. Include pytest tests.

4. **Frontend UI**: Create `/admin/backup` page with backup list table, detail dialog, and download button. Add "Backup" to the admin navigation. Include Jest/RTL unit tests and Playwright e2e tests.

5. **Deployment**: Update `scripts/deploy-container-apps.sh` to deploy the backup Container Apps Job. Update CI/CD pipeline for the new project.

Write tests alongside each component. Verify all quality checks pass (ruff, pytest, eslint, tsc, jest, build).

**Living Document Update**: After completing implementation, update this plan document (`docs/project/plan/034-api-center-backup.md`):
1. Change the status banner at the top to `> **✅ Status: Complete**`
2. Add a row to the Status History table with the completion date and a summary
3. Record any technical decisions made under "Technical Decisions"
4. Note any deviations from the plan under "Deviations from Plan"
5. Record test/validation results under "Validation Results"
```
