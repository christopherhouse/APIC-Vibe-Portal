# CI/CD Pipeline

## Overview

The CI/CD pipeline consists of five GitHub Actions workflows:

| Workflow              | File               | Trigger                                 | Purpose                                  |
| --------------------- | ------------------ | --------------------------------------- | ---------------------------------------- |
| CI                    | `ci.yml`           | PR + push to `main`                     | Lint, typecheck, test, build             |
| Deploy Infrastructure | `deploy-infra.yml` | Push to `main` (infra changes) + manual | Bicep → Azure                            |
| Deploy Application    | `deploy-app.yml`   | Push to `main` (src changes) + manual   | Docker build → ACR → Container Apps      |
| Load Test             | `load-test.yml`    | After deploy-app + manual               | JMeter load tests via Azure Load Testing |
| PR Checks             | `pr-checks.yml`    | PR events                               | Labeling, size checks, plan references   |

## Environments

Three GitHub environments with progressive approval gates:

| Environment | Deploy Trigger               | Approval Required |
| ----------- | ---------------------------- | ----------------- |
| `dev`       | Auto on push to `main`       | No                |
| `staging`   | Manual (`workflow_dispatch`) | Yes               |
| `prod`      | Manual (`workflow_dispatch`) | Yes               |

### Setup

1. **Settings → Environments → Create** three environments: `dev`, `staging`, `prod`
2. For `staging` and `prod`: enable **Required reviewers** and add approvers

## Azure Authentication (OIDC)

Workflows authenticate to Azure using OpenID Connect (OIDC) — no stored Azure credentials.

### Setup Steps

#### 1. Create Entra ID App Registration

```bash
az login
APP_NAME="apic-vibe-portal-github-actions"
APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
```

#### 2. Configure Federated Credentials

```bash
GITHUB_REPO="christopherhouse/APIC-Vibe-Portal"

# Main branch
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_REPO"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Pull requests (for CI validation)
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-actions-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_REPO"':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

#### 3. Assign RBAC Roles

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
az role assignment create \
  --assignee "$SP_ID" \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"
```

## GitHub Secrets & Variables

### Repository Secrets

| Secret                  | Description                         |
| ----------------------- | ----------------------------------- |
| `AZURE_CLIENT_ID`       | Entra ID app registration client ID |
| `AZURE_TENANT_ID`       | Azure tenant ID                     |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID               |

### Environment Variables (per environment)

| Variable               | dev example                                     | Description                 |
| ---------------------- | ----------------------------------------------- | --------------------------- |
| `AZURE_RESOURCE_GROUP` | `rg-apic-vibe-portal-dev`                       | Resource group name         |
| `MSAL_CLIENT_ID`       | `12345678-...`                                  | SPA client ID               |
| `MSAL_AUTHORITY`       | `https://login.microsoftonline.com/<tenant>`    | Entra authority             |
| `MSAL_REDIRECT_URI`    | `https://apic-portal-dev.azurecontainerapps.io` | Redirect URI                |
| `BFF_API_SCOPE`        | `api://<bff-client-id>/.default`                | BFF OAuth scope             |
| `LOADTEST_CLIENT_ID`   | `<sp-client-id>`                                | Load test service principal |
| `LOADTEST_TOKEN_SCOPE` | `api://<bff-client-id>/.default`                | Load test token scope       |

### Environment Secrets (per environment)

| Secret                   | Description                               |
| ------------------------ | ----------------------------------------- |
| `LOADTEST_CLIENT_SECRET` | Load test service principal client secret |

## Workflow Details

### CI (`ci.yml`)

Runs on every PR and push to `main`:

1. **lint** — ESLint + Prettier (frontend/shared), Ruff (BFF)
2. **typecheck** — `tsc --noEmit`
3. **test-frontend** — `npm run test`
4. **e2e-frontend** — Playwright E2E tests
5. **test-bff** — `uv run pytest`
6. **build-frontend** — `npm run build`
7. **build-bff** — Docker build

### Deploy Infrastructure (`deploy-infra.yml`)

Triggered when `infra/**` changes or manually:

1. **validate** — `az deployment group validate`
2. **deploy-dev** — Deploys Bicep to dev (auto)
3. **deploy-staging** — Deploys Bicep to staging (manual approval)
4. **deploy-prod** — Deploys Bicep to prod (manual approval)

### Deploy Application (`deploy-app.yml`)

Triggered when `src/**` changes or manually:

1. **build-and-push-frontend** — Build Docker image → push to ACR
2. **build-and-push-bff** — Build Docker image → push to ACR
3. **deploy-dev** — `scripts/deploy-container-apps.sh` (auto)
4. **deploy-staging** — Container Apps update (manual approval)
5. **deploy-prod** — Container Apps update (manual approval)

### Docker Images

Both images use multi-stage builds:

- **Frontend**: `node:24-alpine` build → `node:24-alpine` production; non-root user; health check
- **BFF**: `python:3.14-slim` build → `python:3.14-slim` production; non-root user; health check

Images are built once and promoted across environments using runtime configuration.

### Container Apps Deployment

Container Apps are deployed via `scripts/deploy-container-apps.sh` (not directly in Bicep). The script:

- Creates Container Apps if they don't exist
- Updates existing apps with new image tags
- Configures ingress, scaling rules, managed identity, and environment variables
- Outputs application URLs

## Manual Deployments

1. **Actions** → select workflow (e.g., "Deploy Application")
2. **Run workflow** → select environment
3. For staging/prod: workflow pauses for reviewer approval

## Troubleshooting

| Problem                       | Fix                                                        |
| ----------------------------- | ---------------------------------------------------------- |
| OIDC auth fails               | Check federated credential `subject` matches repo + branch |
| Container Apps deploy fails   | Verify managed identity has AcrPull + required RBAC roles  |
| Build fails (Node.js version) | Ensure `.nvmrc` specifies Node.js >= 24                    |
| Build fails (Python version)  | Ensure `.python-version` specifies Python 3.14             |

## Related

- [[Architecture]] — Container Apps and ACR architecture
- [[Authentication and RBAC]] — Entra ID app registration setup
- [[Load Testing]] — Load test workflow details
