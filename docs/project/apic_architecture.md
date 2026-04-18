# APIC Vibe Portal AI - Architecture Document

## Overview

Multi-agent API portal built on:

- Azure API Center
- Azure AI Search
- Azure OpenAI
- Foundry Agent Service
- Azure Container Apps
- Azure Cosmos DB (serverless)
- Azure Cache for Redis (API catalog response cache)

## Architecture Diagram

Browser -> Next.js -> BFF (Python/FastAPI) -> APIC + AI Search + Foundry Agents + Cosmos DB
↕
Azure Cache for Redis (cache)

## Components

- Frontend (Next.js SPA)
- Backend (BFF) — Python 3.14, FastAPI, managed with UV
- Agent Layer (Foundry)
- Search Layer (AI Search)
- Observability (App Insights)
- Persistence (Cosmos DB serverless — chat sessions, governance snapshots, analytics)
- **Response Cache (Azure Cache for Redis)** — caches API Center read results in the BFF to reduce latency and API Center call volume; falls back to an in-memory cache for local development when `REDIS_HOST` is not set

## Caching

The BFF uses **Azure Cache for Redis** (`Microsoft.Cache/redis`) as a response cache for all Azure API Center read operations.

| Entity                     | Cache TTL |
| -------------------------- | --------- |
| API list                   | 2 min     |
| API detail / versions      | 5 min     |
| Specifications             | 10 min    |
| Environments / Deployments | 15 min    |

**Authentication**: Entra ID only. The user-assigned managed identity is granted the built-in `Data Owner` access policy on the Redis instance. Access keys are disabled (`disableAccessKeyAuthentication: true`). The BFF acquires short-lived Entra tokens via `DefaultAzureCredential` and refreshes them automatically.

**SKUs**: `Basic/C0` (250 MB) for dev, `Standard/C1` (1 GB) for staging/prod.

**Connection**: `REDIS_HOST` and `REDIS_PORT=6380` are set as environment variables on the BFF container app at deploy time. `AZURE_CLIENT_ID` is also set to ensure `DefaultAzureCredential` selects the correct user-assigned MI for token acquisition.

## ⚠️ Azure Cache for Redis — Deprecation Risk Acknowledgment

**Date**: 2026-04-16

**Context**: Azure Managed Redis (`Microsoft.Cache/redisEnterprise`) was the original cache service but consistently fails to deploy — both via CI/CD (Bicep/ARM) and manually in the Azure Portal. To unblock deployment, we switched to Azure Cache for Redis (`Microsoft.Cache/redis`), which is **deprecated** but still functional and deployable.

**Known Risks**:

- Azure Cache for Redis is officially deprecated and will eventually reach end-of-life
- No new features or improvements will be made to the service
- Microsoft recommends migrating to Azure Managed Redis (which we cannot currently deploy)

**Remediation Plan**:

1. **Monitor**: Track Azure Managed Redis deployment issues — check monthly for fixes or GA status improvements
2. **Retry**: Periodically attempt Azure Managed Redis deployment to see if the issue is resolved
3. **Migrate**: Once Azure Managed Redis deploys successfully, migrate back by restoring the `Microsoft.Cache/redisEnterprise` module
4. **Fallback**: If Azure Cache for Redis reaches EOL before AMR is deployable, evaluate alternative caching strategies (e.g., Cosmos DB-backed cache, in-memory with sticky sessions)

## Key Decisions

- BFF required for orchestration
- Hybrid search for retrieval
- Multi-agent design
- Azure Cache for Redis as interim cache solution — Azure Managed Redis (preferred) fails to deploy; using deprecated ACR until AMR deployment issues are resolved (see deprecation risk section above)
- Cache-aside pattern with graceful degradation — Redis errors are logged and treated as cache misses; BFF never fails due to a cache unavailability

## Security

- Entra ID
- RBAC + security trimming
- Per-container User-Assigned Managed Identities (UAMI) — each Container App has its own UAMI for least-privilege access:
  - **Frontend UAMI** (`{prefix}-id-frontend-{env}-{suffix}`): AcrPull on ACR only
  - **BFF UAMI** (`{prefix}-id-bff-{env}-{suffix}`): AcrPull on ACR plus RBAC roles on Key Vault, API Center, AI Search, OpenAI, Cosmos DB, Foundry, and Redis
- Redis authenticated via Entra MI only (no embedded connection strings or access keys)

## Deployment

- Azure Container Apps (each with a dedicated UAMI)
- ACR (image pull via per-container UAMI `--registry-identity` using ARM resource IDs)
- Key Vault

## Data Architecture

See the detailed data governance documentation:

- [Storage Strategy](../../docs/architecture/storage-strategy.md) — Storage decisions by data class (chat sessions, governance snapshots, analytics)
- [Data Retention Policy](../../docs/architecture/data-retention-policy.md) — Retention periods, soft-delete, and GDPR erasure
- [PII Handling](../../docs/architecture/pii-handling.md) — PII field identification, masking, and redaction rules
- [Cosmos DB Indexing](../../docs/architecture/cosmos-db-indexing.md) — Partitioning, indexing policies, and query optimization
- [Schema Versioning](../../docs/architecture/schema-versioning.md) — Schema evolution and lazy migration patterns
