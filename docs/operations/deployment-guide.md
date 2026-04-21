# Deployment Guide

This guide describes how to deploy the APIC Vibe Portal AI to Azure Container Apps using the CI/CD pipeline or manually.

## Overview

The portal consists of two containerized services:

| Service  | Technology            | Container  |
| -------- | --------------------- | ---------- |
| Frontend | Next.js 16            | `frontend` |
| BFF      | Python 3.14 + FastAPI | `bff`      |

Both services are deployed to **Azure Container Apps** and pull images from **Azure Container Registry (ACR)**.

Infrastructure is provisioned with **Bicep** (`infra/` directory) and Container Apps are deployed via a **Bash script** after infrastructure provisioning.

## Prerequisites

- Azure CLI (`az`) installed and authenticated (`az login`)
- Docker installed (for local builds)
- Access to the Azure subscription and resource group
- GitHub Actions secrets configured (for CI/CD deployment)

## Environment Configuration

Copy `.env.example` to `.env.local` (never commit `.env.local`):

```bash
cp .env.example .env.local
```

Required environment variables (aligned with `.env.example`):

| Variable                                | Description                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------------ |
| `MSAL_CLIENT_ID`                        | SPA app registration client ID (served to browser via `/api/config/msal`)      |
| `MSAL_AUTHORITY`                        | Entra ID authority URL                                                         |
| `MSAL_REDIRECT_URI`                     | Redirect URI registered in Entra ID                                            |
| `BFF_API_SCOPE`                         | BFF API scope for access token acquisition                                     |
| `BFF_URL`                               | BFF base URL (frontend server-side proxy; defaults to `http://localhost:8000`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection string (served via `/api/config/telemetry`)            |
| `AZURE_OPENAI_ENDPOINT`                 | Azure OpenAI endpoint URL                                                      |
| `AZURE_OPENAI_API_KEY`                  | Azure OpenAI API key (use Managed Identity in production)                      |
| `AZURE_SEARCH_ENDPOINT`                 | Azure AI Search endpoint                                                       |
| `AZURE_SEARCH_API_KEY`                  | Azure AI Search admin key (use Managed Identity in production)                 |
| `AZURE_COSMOS_ENDPOINT`                 | Azure Cosmos DB endpoint                                                       |
| `AZURE_COSMOS_KEY`                      | Cosmos DB key (use Managed Identity in production)                             |
| `AZURE_APIC_ENDPOINT`                   | Azure API Center data plane endpoint                                           |
| `AZURE_APIC_SERVICE_NAME`               | Azure API Center service name                                                  |
| `AZURE_APIC_SUBSCRIPTION_ID`            | Azure subscription containing API Center                                       |
| `AZURE_APIC_RESOURCE_GROUP`             | Resource group for API Center                                                  |

> **Security**: Store all secrets in **Azure Key Vault** and reference them in Container Apps secrets. Never commit secrets to source control. Production deployments use **Managed Identity** — API keys are only needed for local development.

## Automated Deployment (CI/CD)

Deployments are triggered automatically via GitHub Actions on push to `main`:

1. **Build** — Docker images are built for frontend and BFF
2. **Push** — Images are pushed to ACR
3. **Deploy** — Container Apps are updated with the new images

See `.github/workflows/` for the full pipeline definition.

### Required GitHub Secrets

| Secret              | Purpose                             |
| ------------------- | ----------------------------------- |
| `AZURE_CREDENTIALS` | Service principal JSON for az login |
| `ACR_LOGIN_SERVER`  | ACR login server URL                |
| `RESOURCE_GROUP`    | Target resource group               |
| `FRONTEND_APP_NAME` | Container App name (frontend)       |
| `BFF_APP_NAME`      | Container App name (BFF)            |

## Manual Deployment

### Step 1: Provision Infrastructure (first time only)

```bash
cd infra
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file main.bicep \
  --parameters @parameters.json
```

### Step 2: Build Docker Images

```bash
# Frontend
docker build -t <acr-name>.azurecr.io/frontend:latest src/frontend

# BFF
docker build -t <acr-name>.azurecr.io/bff:latest src/bff
```

### Step 3: Push Images to ACR

```bash
az acr login --name <acr-name>
docker push <acr-name>.azurecr.io/frontend:latest
docker push <acr-name>.azurecr.io/bff:latest
```

### Step 4: Deploy Container Apps

```bash
# Update frontend
az containerapp update \
  --name <frontend-app-name> \
  --resource-group <resource-group> \
  --image <acr-name>.azurecr.io/frontend:latest

# Update BFF
az containerapp update \
  --name <bff-app-name> \
  --resource-group <resource-group> \
  --image <acr-name>.azurecr.io/bff:latest
```

### Step 5: Verify Deployment

```bash
# Get the frontend URL
az containerapp show \
  --name <frontend-app-name> \
  --resource-group <resource-group> \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

Navigate to the URL and confirm the portal loads correctly.

## Rollback Procedure

To roll back to a previous image:

```bash
# List available revisions
az containerapp revision list \
  --name <app-name> \
  --resource-group <resource-group>

# Activate a previous revision
az containerapp revision activate \
  --revision <revision-name> \
  --resource-group <resource-group>
```

## Health Checks

Both Container Apps are configured with HTTP health check probes:

| Service  | Health endpoint                    |
| -------- | ---------------------------------- |
| BFF      | `GET /health` → `{"status": "ok"}` |
| Frontend | `GET /` → HTTP 200                 |

If a health check fails, Container Apps automatically routes traffic to healthy replicas.

## Related Documentation

- **[Monitoring Runbook](monitoring-runbook.md)**
- **[Scaling Guide](scaling-guide.md)**
- **[Troubleshooting](troubleshooting.md)**
- **[Rollback and Recovery](backup-recovery.md)**
