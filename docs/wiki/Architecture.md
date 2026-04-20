# Architecture

## Overview

The APIC Vibe Portal AI is a multi-tier, multi-agent API portal. Requests flow from the browser through a Next.js frontend to a Python/FastAPI Backend-for-Frontend (BFF), which orchestrates calls to Azure API Center, AI Search, Foundry Agents, Cosmos DB, OpenAI, and a Redis cache.

## Architecture Diagram

```
Browser
  │
  ▼
Next.js SPA (Azure Container Apps)
  │  MSAL / Entra ID auth
  ▼
BFF — Python 3.14 / FastAPI (Azure Container Apps)
  ├──► Azure API Center          (API catalog)
  ├──► Azure AI Search           (hybrid search + semantic ranking)
  ├──► Azure OpenAI              (LLM completions)
  ├──► Foundry Agent Service     (multi-agent orchestration)
  ├──► Azure Cosmos DB           (chat sessions, governance, analytics)
  ├──► Azure Cache for Redis     (response cache for API Center reads)
  └──► Azure Key Vault           (secrets via Managed Identity)

Both containers ──► Azure Application Insights  (logs, traces, metrics)
```

## Components

### Frontend — Next.js SPA

| Property   | Value                                           |
| ---------- | ----------------------------------------------- |
| Framework  | Next.js 16 (App Router)                         |
| Language   | TypeScript 6.0 (strict mode)                    |
| UI Library | Material UI (MUI) + Emotion                     |
| Auth       | MSAL.js (Microsoft Authentication Library)      |
| Testing    | Jest + React Testing Library · Playwright (E2E) |
| Hosting    | Azure Container Apps                            |

The frontend is a single Docker image that is built once and promoted across environments. MSAL configuration (client ID, authority, redirect URI) is injected at runtime via environment variables — not baked in at build time. See [[Runtime Configuration]] for details.

### BFF — Python/FastAPI

| Property        | Value                            |
| --------------- | -------------------------------- |
| Language        | Python 3.14                      |
| Framework       | FastAPI                          |
| Package Manager | UV                               |
| Auth            | JWT validation (Entra ID tokens) |
| Testing         | pytest                           |
| Hosting         | Azure Container Apps             |

The BFF acts as a secure gateway between the frontend and Azure services. It:

- Validates Entra ID JWT tokens on every request
- Enforces RBAC (`Portal.Admin`, `Portal.Maintainer`, `Portal.User`)
- Orchestrates multi-agent workflows via Foundry Agent Service
- Caches API Center results in Redis to reduce latency
- Stores chat sessions and governance snapshots in Cosmos DB

### AI / Agent Layer

- **Azure OpenAI** — LLM completions for the chat assistant
- **Foundry Agent Service** — Multi-agent orchestration (search agent, governance agent, comparison agent)
- **Azure AI Search** — Hybrid search (keyword + vector) with semantic ranking over the API catalog

### Persistence

- **Azure Cosmos DB** (serverless, NoSQL API) — chat sessions, governance snapshots, analytics events
- **Azure Cache for Redis** — Response cache for API Center reads; falls back to in-memory for local development

### Infrastructure

- **Azure Container Registry (ACR)** — Docker image storage
- **Azure Container Apps** — Serverless container hosting
- **Azure Key Vault** — Secret storage (never commit secrets to source control!)
- **User-Assigned Managed Identities (UAMI)** — Each Container App has its own UAMI for least-privilege access

## Security Model

- **Authentication**: Entra ID (Azure AD) — all non-public routes require a valid JWT
- **Authorization**: RBAC via App Roles in the JWT `roles` claim
- **Secrets**: Managed Identity + Key Vault (no embedded connection strings)
- **Network**: Azure Container Apps handles TLS termination and CORS
- **Identity segregation**: Frontend UAMI has AcrPull only; BFF UAMI has additional roles for Key Vault, API Center, AI Search, OpenAI, Cosmos DB, Foundry, and Redis

See [[Authentication and RBAC]] and [[Security]] for details.

## Key Design Decisions

| Decision                              | Rationale                                                                                     |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| BFF required                          | Keeps secrets server-side; enables token exchange and orchestration                           |
| Hybrid search                         | Combines keyword precision with vector semantic understanding                                 |
| Multi-agent design                    | Separates concerns: search, governance, comparison, orchestration                             |
| Cache-aside with graceful degradation | Redis errors are treated as cache misses — BFF never fails due to cache unavailability        |
| Azure Cache for Redis (interim)       | Azure Managed Redis fails to deploy; deprecated ACR used until AMR is stable. See [[Caching]] |
| Build-once Docker images              | Same image promoted across dev/staging/prod; config injected at runtime                       |
| Per-container UAMI                    | Least-privilege identity for each workload                                                    |

## Repository Structure

```
/
├── src/
│   ├── frontend/        # Next.js 16 SPA
│   ├── bff/             # Python 3.14 + FastAPI
│   ├── shared/          # Shared TypeScript types/utilities
│   ├── apic_client/     # Azure API Center client
│   └── indexer/         # AI Search indexing pipeline
├── infra/               # Bicep IaC templates
├── .github/
│   ├── workflows/       # CI/CD pipelines
│   └── agents/          # Custom Copilot agents
├── docs/
│   ├── project/         # Product charter, architecture, spec, implementation plan
│   ├── architecture/    # Data architecture docs
│   ├── security/        # Threat models, security policy
│   └── wiki/            # Wiki source files (published here)
├── scripts/             # Developer helper scripts
└── tests/               # Load tests (JMeter)
```

## Data Architecture

See [[Data Architecture]] for the detailed storage strategy, partitioning, retention, PII handling, and schema versioning.
