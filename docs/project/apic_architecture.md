# APIC Vibe Portal AI - Architecture Document

## Overview

Multi-agent API portal built on:

- Azure API Center
- Azure AI Search
- Azure OpenAI
- Foundry Agent Service
- Azure Container Apps
- Azure Cosmos DB (serverless)
- Azure Managed Redis (API catalog response cache)

## Architecture Diagram

Browser -> Next.js -> BFF (Python/FastAPI) -> APIC + AI Search + Foundry Agents + Cosmos DB
                                             ↕
                                   Azure Managed Redis (cache)

## Components

- Frontend (Next.js SPA)
- Backend (BFF) — Python 3.14, FastAPI, managed with UV
- Agent Layer (Foundry)
- Search Layer (AI Search)
- Observability (App Insights)
- Persistence (Cosmos DB serverless — chat sessions, governance snapshots, analytics)
- **Response Cache (Azure Managed Redis)** — caches API Center read results in the BFF to reduce latency and API Center call volume; falls back to an in-memory cache for local development when `REDIS_HOST` is not set

## Caching

The BFF uses **Azure Managed Redis** (`Microsoft.Cache/redisEnterprise`) as a response cache for all Azure API Center read operations.

| Entity | Cache TTL |
|--------|-----------|
| API list | 2 min |
| API detail / versions | 5 min |
| Specifications | 10 min |
| Environments / Deployments | 15 min |

**Authentication**: Entra ID only. The user-assigned managed identity is granted the built-in `default` data-plane access policy on the Redis database. Access keys are disabled (`accessKeysAuthentication: Disabled`). The BFF acquires short-lived Entra tokens via `DefaultAzureCredential` and refreshes them automatically.

**SKUs**: `Balanced_B0` (0.5 GB) for dev, `Balanced_B1` (1 GB) for staging/prod.

**Connection**: `REDIS_HOST` and `REDIS_PORT=10000` are set as environment variables on the BFF container app at deploy time. `AZURE_CLIENT_ID` is also set to ensure `DefaultAzureCredential` selects the correct user-assigned MI for token acquisition.

## Key Decisions

- BFF required for orchestration
- Hybrid search for retrieval
- Multi-agent design
- Azure Managed Redis over Azure Cache for Redis — the latter is deprecated; AMR uses the Redis Enterprise cluster architecture with Entra ID authentication
- Cache-aside pattern with graceful degradation — Redis errors are logged and treated as cache misses; BFF never fails due to a cache unavailability

## Security

- Entra ID
- RBAC + security trimming
- Redis authenticated via Entra MI only (no embedded connection strings or access keys)

## Deployment

- Azure Container Apps
- ACR
- Key Vault
