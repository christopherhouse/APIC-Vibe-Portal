# Getting Started

This guide walks you through setting up a local development environment for the APIC Vibe Portal.

## Prerequisites

| Tool      | Version                      | Install                                                                            |
| --------- | ---------------------------- | ---------------------------------------------------------------------------------- | --- |
| Node.js   | >= 24 (see `.nvmrc`)         | [nodejs.org](https://nodejs.org) or `nvm install`                                  |
| npm       | >= 10                        | Included with Node.js                                                              |
| Python    | 3.14 (see `.python-version`) | [python.org](https://python.org) or `pyenv install`                                |
| UV        | latest                       | `curl -LsSf https://astral.sh/uv/install.sh                                        | sh` |
| Azure CLI | latest                       | [Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) |
| Docker    | latest                       | [docker.com](https://docker.com) (optional, for container builds)                  |
| Git       | >= 2.40                      | [git-scm.com](https://git-scm.com)                                                 |

## Clone & Install

```bash
# 1. Clone the repository
git clone https://github.com/christopherhouse/APIC-Vibe-Portal.git
cd APIC-Vibe-Portal

# 2. Install frontend + shared TypeScript dependencies
npm install

# 3. Install BFF Python dependencies
cd src/bff
uv sync
cd ../..
```

## Configure Local Environment

### Frontend

Create `src/frontend/.env.local`:

```env
MSAL_CLIENT_ID=<your-spa-app-client-id>
MSAL_AUTHORITY=https://login.microsoftonline.com/<your-tenant-id>
MSAL_REDIRECT_URI=http://localhost:3000
BFF_API_SCOPE=api://<your-bff-client-id>/.default
```

> **Tip**: See [[Authentication and RBAC]] → Local Development Setup for step-by-step instructions on creating the Entra ID app registrations.

### BFF

Create `src/bff/.env` (or export in your shell):

```env
BFF_ENTRA_TENANT_ID=<your-tenant-id>
BFF_ENTRA_CLIENT_ID=<your-bff-client-id>
BFF_ENTRA_AUDIENCE=api://<your-bff-client-id>

APIC_SUBSCRIPTION_ID=<azure-subscription-id>
APIC_RESOURCE_GROUP=<resource-group-name>
APIC_SERVICE_NAME=<api-center-service-name>

AZURE_AI_SEARCH_ENDPOINT=https://<search-name>.search.windows.net
AZURE_AI_SEARCH_INDEX_NAME=apic-catalog

AZURE_OPENAI_ENDPOINT=https://<openai-name>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=<deployment-name>

COSMOS_DB_ENDPOINT=https://<cosmos-name>.documents.azure.com:443/
COSMOS_DB_DATABASE=apic-vibe-portal

# Optional — Redis (leave unset to use in-memory fallback for local dev)
# REDIS_HOST=<redis-name>.redis.cache.windows.net
# REDIS_PORT=6380
```

## Run the Dev Servers

### Frontend (Next.js)

```bash
npm run dev --workspace=@apic-vibe-portal/frontend
# Runs on http://localhost:3000
```

### BFF (FastAPI)

```bash
cd src/bff
uv run fastapi dev
# Runs on http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

Both servers support hot-reload.

## Common Commands

### Lint

```bash
# Frontend + Shared (ESLint + Prettier check)
npm run lint
npm run format:check

# BFF (Ruff)
cd src/bff && uv run ruff check . && uv run ruff format --check .
```

### Format

```bash
# Frontend + Shared
npm run format

# BFF
cd src/bff && uv run ruff format .
```

### Type Check

```bash
# Frontend + Shared
npx tsc --noEmit
```

### Tests

```bash
# Frontend + Shared unit tests
npm run test

# Frontend E2E tests (requires dev server running)
npm run test:e2e --workspace=@apic-vibe-portal/frontend

# BFF unit tests
cd src/bff && uv run pytest
```

### Build

```bash
# Frontend (production build)
npm run build

# BFF compile check
cd src/bff && uv run python -m compileall .
```

## Docker Builds (Optional)

```bash
# Build frontend image
docker build -t apic-portal-frontend src/frontend

# Build BFF image
docker build -t apic-portal-bff src/bff
```

## Troubleshooting

| Problem                        | Fix                                                                  |
| ------------------------------ | -------------------------------------------------------------------- |
| `nvm` not found                | Install nvm first, then run `nvm install` in the repo root           |
| `uv` not found                 | Run the UV install script (see Prerequisites)                        |
| Frontend can't reach BFF       | Ensure BFF is running on port 8000; check `.env.local` proxy config  |
| MSAL redirect loop             | Verify `MSAL_REDIRECT_URI=http://localhost:3000` in `.env.local`     |
| `roles` claim missing in token | Assign yourself an app role in Entra ID Enterprise applications      |
| Redis connection refused       | Leave `REDIS_HOST` unset — BFF falls back to in-memory cache locally |

## Next Steps

- [[Authentication and RBAC]] — Set up Entra ID app registrations
- [[Architecture]] — Understand the system design
- [[Contributing]] — Branch strategy and coding conventions
