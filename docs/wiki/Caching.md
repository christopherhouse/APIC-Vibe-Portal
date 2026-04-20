# Caching

## Overview

The BFF uses **Azure Cache for Redis** as a response cache for all Azure API Center read operations. This reduces latency and API Center call volume. Cache errors are treated as cache misses — the BFF never fails due to cache unavailability.

## Cache TTLs

| Entity                     | Cache TTL  |
| -------------------------- | ---------- |
| API list                   | 2 minutes  |
| API detail / versions      | 5 minutes  |
| Specifications             | 10 minutes |
| Environments / Deployments | 15 minutes |

## Authentication

Redis is authenticated using **Entra ID Managed Identity only**. Access keys are disabled:

```bicep
disableAccessKeyAuthentication: true
```

The BFF's UAMI is granted the built-in `Data Owner` access policy on the Redis instance. Tokens are acquired via `DefaultAzureCredential` and refreshed automatically.

## Environment Configuration

| Variable          | Description                                                                |
| ----------------- | -------------------------------------------------------------------------- |
| `REDIS_HOST`      | Redis hostname (e.g., `myredis.redis.cache.windows.net`)                   |
| `REDIS_PORT`      | Redis port (default: `6380`)                                               |
| `AZURE_CLIENT_ID` | UAMI client ID — ensures `DefaultAzureCredential` picks the right identity |

**Local development**: Leave `REDIS_HOST` unset. The BFF falls back to an in-memory cache automatically.

## SKU Selection

| Environment  | SKU         | Size   |
| ------------ | ----------- | ------ |
| dev          | Basic/C0    | 250 MB |
| staging/prod | Standard/C1 | 1 GB   |

## Cache-Aside Pattern

```
Request
  │
  ▼
BFF — check Redis
  │
  ├── Cache HIT ──► Return cached response (fast path)
  │
  └── Cache MISS ──► Call Azure API Center ──► Store in Redis ──► Return response
                                                    │
                                    Redis error ──► Log warning, treat as miss, continue
```

Redis errors are **never** propagated to the caller. The BFF logs the error and falls through to the underlying API call.

## ⚠️ Deprecation Risk: Azure Cache for Redis

**Date**: 2026-04-16

Azure Managed Redis (`Microsoft.Cache/redisEnterprise`) is the preferred cache service, but it **consistently fails to deploy** — both via CI/CD (Bicep/ARM) and manually in the Azure Portal. As a workaround, we switched to **Azure Cache for Redis** (`Microsoft.Cache/redis`), which is deprecated but still functional and deployable.

### Known Risks

- Azure Cache for Redis is officially deprecated — no new features will be added
- Microsoft recommends migrating to Azure Managed Redis

### Remediation Plan

1. **Monitor**: Check monthly for Azure Managed Redis deployment fixes or GA status improvements
2. **Retry**: Periodically attempt Azure Managed Redis deployment
3. **Migrate**: Once AMR deploys successfully, restore `Microsoft.Cache/redisEnterprise` module in Bicep
4. **Fallback**: If Azure Cache for Redis reaches EOL before AMR is deployable, evaluate Cosmos DB-backed cache or in-memory with sticky sessions

## Related

- [[Architecture]] — Caching in the overall architecture
- [[Getting Started]] — Local development without Redis
