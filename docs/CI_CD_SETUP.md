# CI/CD Setup Guide

This document describes the CI/CD pipeline configuration for the APIC Vibe Portal and how to set it up.

## Overview

The CI/CD pipeline consists of five GitHub Actions workflows:

1. **CI** (`ci.yml`) — Runs lint, test, and build checks on PRs and pushes to main
2. **Deploy Infrastructure** (`deploy-infra.yml`) — Deploys Bicep templates to Azure
3. **Deploy Application** (`deploy-app.yml`) — Builds Docker images and deploys to Container Apps
4. **Load Test** (`load-test.yml`) — Runs JMeter load tests via Azure App Testing after deployment
5. **PR Checks** (`pr-checks.yml`) — Automated PR quality gates (labeling, size checks, plan references)

## GitHub Environments

The pipeline uses three GitHub environments with approval gates:

- **dev** — Automatically deploys on push to `main`
- **staging** — Requires manual approval (workflow_dispatch only)
- **prod** — Requires manual approval (workflow_dispatch only)

### Setting Up Environments

1. Go to **Settings** > **Environments** in your GitHub repository
2. Create three environments: `dev`, `staging`, `prod`
3. For `staging` and `prod`:
   - Enable **Required reviewers**
   - Add reviewers who must approve deployments

## Azure Authentication (OIDC)

The pipeline uses OpenID Connect (OIDC) for Azure authentication, eliminating the need to store Azure credentials as secrets.

### Prerequisites

- An Azure subscription
- An Entra ID (Azure AD) app registration
- Federated credentials configured for GitHub Actions

### Setup Steps

#### 1. Create an Entra ID App Registration

```bash
# Login to Azure
az login

# Create app registration
APP_NAME="apic-vibe-portal-github-actions"
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --query appId -o tsv)

echo "App ID: $APP_ID"

# Create service principal
SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
echo "Service Principal ID: $SP_ID"
```

#### 2. Configure Federated Credentials for GitHub Actions

```bash
# Get your GitHub repository (format: owner/repo)
GITHUB_REPO="christopherhouse/APIC-Vibe-Portal"

# Create federated credential for main branch
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_REPO"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated credential for pull requests (optional, for validation)
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-actions-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_REPO"':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

#### 3. Assign Azure RBAC Roles

Grant the service principal permissions to deploy resources:

```bash
# Get your subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Assign Contributor role for infrastructure deployment
az role assignment create \
  --assignee "$SP_ID" \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID"

# Assign AcrPush role for pushing Docker images (if ACR already exists)
# Replace <acr-resource-id> with your ACR resource ID
# az role assignment create \
#   --assignee "$SP_ID" \
#   --role "AcrPush" \
#   --scope "<acr-resource-id>"
```

#### 4. Create Resource Groups

Create resource groups for each environment:

```bash
az group create --name "rg-apic-vibe-portal-dev" --location "eastus"
az group create --name "rg-apic-vibe-portal-staging" --location "eastus"
az group create --name "rg-apic-vibe-portal-prod" --location "eastus"
```

#### 5. Configure GitHub Secrets and Environment Variables

##### Repository Secrets

Add the following secrets to your GitHub repository (**Settings** > **Secrets and variables** > **Actions**):

| Secret Name             | Value               | Description                         |
| ----------------------- | ------------------- | ----------------------------------- |
| `AZURE_CLIENT_ID`       | `<APP_ID>`          | Entra ID app registration client ID |
| `AZURE_TENANT_ID`       | `<TENANT_ID>`       | Azure tenant ID                     |
| `AZURE_SUBSCRIPTION_ID` | `<SUBSCRIPTION_ID>` | Azure subscription ID               |

Get your tenant ID:

```bash
az account show --query tenantId -o tsv
```

##### Environment Variables

For each GitHub environment (dev, staging, prod), add environment-scoped variables (**Settings** > **Environments** > select environment > **Environment variables**):

| Variable Name          | Value (dev)               | Value (staging)               | Value (prod)               | Description                              |
| ---------------------- | ------------------------- | ----------------------------- | -------------------------- | ---------------------------------------- |
| `AZURE_RESOURCE_GROUP` | `rg-apic-vibe-portal-dev` | `rg-apic-vibe-portal-staging` | `rg-apic-vibe-portal-prod` | Environment-specific resource group name |
| `LOADTEST_CLIENT_ID`   | `<load-test-sp-client-id>`| `<load-test-sp-client-id>`    | `<load-test-sp-client-id>` | Service principal client ID for load tests |
| `LOADTEST_TOKEN_SCOPE` | `api://<bff-client-id>/.default` | `api://<bff-client-id>/.default` | `api://<bff-client-id>/.default` | Token scope for BFF API |

##### Environment Secrets

For each GitHub environment, add environment-scoped secrets:

| Secret Name              | Value                      | Description                              |
| ------------------------ | -------------------------- | ---------------------------------------- |
| `LOADTEST_CLIENT_SECRET` | `<load-test-sp-secret>`    | Client secret for load test service principal |

This approach uses GitHub environment-scoped variables, which keeps the variable name consistent across environments while allowing environment-specific values.

## Workflow Triggers

### CI Workflow

- **Triggers**: Push to `main`, pull request to `main`
- **Jobs**: lint, typecheck, test-frontend, test-bff, build-frontend, build-bff
- **Purpose**: Ensure code quality and catch issues early

### Deploy Infrastructure Workflow

- **Triggers**:
  - Push to `main` (when `infra/**` changes)
  - Manual trigger via `workflow_dispatch`
- **Jobs**: validate, deploy-dev, deploy-staging, deploy-prod
- **Purpose**: Deploy Bicep templates to Azure

### Deploy Application Workflow

- **Triggers**:
  - Push to `main` (when `src/**` changes)
  - Manual trigger via `workflow_dispatch`
- **Jobs**: build-and-push-frontend, build-and-push-bff, deploy-dev, deploy-staging, deploy-prod
- **Purpose**: Build Docker images and deploy to Container Apps

### Load Test Workflow

- **Triggers**:
  - After successful `Deploy Application` workflow on `main`
  - Manual trigger via `workflow_dispatch`
- **Jobs**: load-test
- **Purpose**: Run JMeter load tests against the BFF API via Azure App Testing
- **Docs**: See [Load Testing Setup Guide](LOAD-TESTING.md)

### PR Checks Workflow

- **Triggers**: Pull request events (opened, synchronize, reopened, edited)
- **Jobs**: labeler, size-check, plan-reference
- **Purpose**: Automated PR quality gates

## Manual Deployments

To manually trigger a deployment:

1. Go to **Actions** in your GitHub repository
2. Select the workflow you want to run (e.g., "Deploy Application")
3. Click **Run workflow**
4. Select the environment (dev, staging, or prod)
5. Click **Run workflow**

For staging and prod deployments, the workflow will pause and wait for approval from designated reviewers.

## Docker Images

The pipeline builds two Docker images:

- **Frontend**: Next.js 16 application (Node.js 24-alpine)
- **BFF**: FastAPI application (Python 3.14-slim)

Both images use multi-stage builds with:

- Separate build and production stages
- Non-root users for security
- Health check endpoints
- Optimized layer caching

## Container Apps Deployment

Container Apps are deployed via the `scripts/deploy-container-apps.sh` bash script after:

1. Infrastructure is provisioned (Bicep)
2. Docker images are built and pushed to ACR

The script:

- Creates Container Apps if they don't exist
- Updates existing Container Apps with new images
- Configures ingress, scaling, and managed identity
- Outputs the application URLs

## Validation

To validate the workflow YAML files locally, install `actionlint`:

```bash
# Install actionlint
brew install actionlint  # macOS
# or download from https://github.com/rhysd/actionlint

# Validate workflows
actionlint .github/workflows/*.yml
```

## Troubleshooting

### OIDC Authentication Fails

- Verify federated credentials are configured correctly
- Check that the `subject` claim matches your repository and branch
- Ensure the app registration has the necessary RBAC roles

### Container Apps Deployment Fails

- Check that the ACR exists and the service principal has `AcrPull` or `AcrPush` role
- Verify the managed identity is configured correctly
- Check Container Apps Environment is provisioned

### Build Failures

- Ensure `.nvmrc` specifies Node.js >= 24
- Ensure `.python-version` specifies Python 3.14
- Check that all dependencies are listed in `package.json` and `pyproject.toml`

## Next Steps

1. Deploy infrastructure: Run the "Deploy Infrastructure" workflow for dev environment
2. Deploy application: Run the "Deploy Application" workflow to push initial images
3. Set up monitoring: Configure Application Insights alerts and dashboards
4. Set up notifications: Configure Slack/Teams notifications for deployment events
