# Load Testing Setup Guide (Azure App Testing)

This document describes the Azure App Testing / Azure Load Testing setup for the APIC Vibe Portal, including the JMeter test plan, CI/CD workflow, and required configuration.

## Overview

The load testing infrastructure consists of:

1. **Azure Load Testing resource** — deployed via Bicep (`infra/modules/load-testing.bicep`)
2. **JMeter test plan** (`tests/load/bff-load-test.jmx`) — tests BFF API endpoints with OAuth 2.0 authentication
3. **Load test config** (`tests/load/load-test-config.yaml`) — Azure Load Testing YAML configuration with failure criteria
4. **GitHub Actions workflow** (`.github/workflows/load-test.yml`) — automates test execution via `azure/load-testing@v1`

## Architecture

```
┌──────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  GitHub Actions   │────▶│  Azure Load Testing   │────▶│   BFF Container  │
│  (load-test.yml) │     │  (JMeter engines)     │     │   App (target)   │
└──────────────────┘     └──────────────────────┘     └─────────────────┘
                                │                              ▲
                                │  OAuth2 client_credentials   │
                                ▼                              │
                         ┌──────────────────┐                  │
                         │    Entra ID       │     Bearer token │
                         │ (token endpoint)  │─────────────────┘
                         └──────────────────┘
```

**Important**: The test client credentials (`LOADTEST_CLIENT_ID`, `LOADTEST_CLIENT_SECRET`) are used **only by JMeter** to acquire tokens. **No new BFF container environment variables are needed.** The BFF validates tokens with its existing `BFF_ENTRA_TENANT_ID`, `BFF_ENTRA_CLIENT_ID`, and `BFF_ENTRA_AUDIENCE` settings.

## Prerequisites

### 1. Azure Infrastructure

Deploy the infrastructure (including the Load Testing resource) first:

```bash
az deployment group create \
  --resource-group <rg-name> \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam
```

This deploys `Microsoft.LoadTestService/loadTests` alongside all other resources.

### 2. Entra ID App Registration for Load Testing

Create a dedicated service principal for load test token acquisition:

```bash
# Create app registration for load testing
LOADTEST_APP_NAME="apic-vibe-portal-loadtest-client"
LOADTEST_APP_ID=$(az ad app create \
  --display-name "$LOADTEST_APP_NAME" \
  --query appId -o tsv)

echo "Load Test Client ID: $LOADTEST_APP_ID"

# Create service principal
az ad sp create --id "$LOADTEST_APP_ID"

# Create a client secret (store in a secure location)
LOADTEST_SECRET=$(az ad app credential reset \
  --id "$LOADTEST_APP_ID" \
  --display-name "load-test-secret" \
  --query password -o tsv)

echo "Load Test Client Secret: $LOADTEST_SECRET"
```

### 3. Assign App Role to Load Test Service Principal

The load test service principal needs the `Portal.User` app role (or equivalent) on the BFF's app registration so the tokens it acquires pass validation:

```bash
# Get the BFF app registration's object ID
BFF_APP_OBJECT_ID=$(az ad app show \
  --id "$BFF_ENTRA_CLIENT_ID" \
  --query id -o tsv)

# Get the Portal.User app role ID from the BFF app registration
ROLE_ID=$(az ad app show \
  --id "$BFF_ENTRA_CLIENT_ID" \
  --query "appRoles[?value=='Portal.User'].id | [0]" -o tsv)

# Get the load test service principal object ID
LOADTEST_SP_ID=$(az ad sp show \
  --id "$LOADTEST_APP_ID" \
  --query id -o tsv)

# Assign the app role
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$LOADTEST_SP_ID/appRoleAssignments" \
  --body "{
    \"principalId\": \"$LOADTEST_SP_ID\",
    \"resourceId\": \"$(az ad sp show --id $BFF_ENTRA_CLIENT_ID --query id -o tsv)\",
    \"appRoleId\": \"$ROLE_ID\"
  }"
```

> **Note**: If the BFF doesn't have app roles configured yet, grant the load test service principal API permissions for the BFF's scope (e.g., `api://<BFF_CLIENT_ID>/.default`) and grant admin consent.

### 4. Configure GitHub Secrets and Variables

Add the following to each GitHub environment (dev, staging, prod):

#### Environment Variables (`vars`)

| Variable               | Value                                  | Description                                  |
| ---------------------- | -------------------------------------- | -------------------------------------------- |
| `LOADTEST_CLIENT_ID`   | `<load-test-app-client-id>`            | Client ID of the load test service principal |
| `LOADTEST_TOKEN_SCOPE` | `api://<BFF_ENTRA_CLIENT_ID>/.default` | Token scope for the BFF API                  |

#### Environment Secrets (`secrets`)

| Secret                   | Value                           | Description                                       |
| ------------------------ | ------------------------------- | ------------------------------------------------- |
| `LOADTEST_CLIENT_SECRET` | `<load-test-app-client-secret>` | Client secret for the load test service principal |

> **Security**: The client secret should also be stored in Azure Key Vault for rotation and auditing purposes.

### 5. RBAC for GitHub Actions

The GitHub Actions OIDC service principal needs the **Load Test Contributor** role on the Azure Load Testing resource:

```bash
# Get the Load Testing resource ID
LOADTEST_RESOURCE_ID=$(az resource show \
  --resource-group <rg-name> \
  --resource-type Microsoft.LoadTestService/loadTests \
  --name <load-test-resource-name> \
  --query id -o tsv)

# Get the GitHub Actions service principal
GH_SP_ID=$(az ad sp show --id "$AZURE_CLIENT_ID" --query id -o tsv)

# Assign Load Test Contributor role
az role assignment create \
  --assignee "$GH_SP_ID" \
  --role "Load Test Contributor" \
  --scope "$LOADTEST_RESOURCE_ID"
```

## Running Load Tests

### Automatic (CI/CD)

The load test runs automatically after a successful deployment to `dev` via the `Deploy Application` workflow.

### Manual

1. Go to **Actions** > **Load Test (Azure App Testing)**
2. Click **Run workflow**
3. Select the target environment
4. Click **Run workflow**

### Locally (JMeter)

For local development/debugging, you can run the JMeter test directly:

```bash
# Set environment variables
export TARGET_HOST="localhost"
export TARGET_PORT="8000"
export PROTOCOL="http"
export TENANT_ID="<your-tenant-id>"
export TOKEN_CLIENT_ID="<load-test-client-id>"
export TOKEN_CLIENT_SECRET="<load-test-client-secret>"
export TOKEN_SCOPE="api://<bff-client-id>/.default"

# Run JMeter
jmeter -n -t tests/load/bff-load-test.jmx \
  -JTARGET_HOST=$TARGET_HOST \
  -JTARGET_PORT=$TARGET_PORT \
  -JPROTOCOL=$PROTOCOL \
  -JTENANT_ID=$TENANT_ID \
  -JTOKEN_CLIENT_ID=$TOKEN_CLIENT_ID \
  -JTOKEN_CLIENT_SECRET=$TOKEN_CLIENT_SECRET \
  -JTOKEN_SCOPE=$TOKEN_SCOPE \
  -JTHREAD_COUNT=5 \
  -JRAMP_UP_SECONDS=10 \
  -JLOOP_COUNT=10
```

## Test Scenarios

The JMeter test plan includes:

| Scenario          | Method | Path                | Auth Required | Description           |
| ----------------- | ------ | ------------------- | ------------- | --------------------- |
| Health Check      | GET    | `/health`           | No            | Basic health endpoint |
| Health Ready      | GET    | `/health/ready`     | No            | Readiness probe       |
| List APIs         | GET    | `/api/catalog`      | Yes           | API catalog browsing  |
| List Environments | GET    | `/api/environments` | Yes           | Environment listing   |

## Failure Criteria

The test is marked as **FAILED** if any of these conditions are met:

| Criterion                          | Threshold  |
| ---------------------------------- | ---------- |
| Overall error rate                 | > 5%       |
| Average response time              | > 2,000 ms |
| 95th percentile response time      | > 5,000 ms |
| Health Check average response time | > 500 ms   |
| List APIs average response time    | > 3,000 ms |

Auto-stop is enabled: the test stops early if error rate exceeds 80% for 60 seconds.

## Files

| File                               | Description                                     |
| ---------------------------------- | ----------------------------------------------- |
| `infra/modules/load-testing.bicep` | Bicep module for Azure Load Testing resource    |
| `tests/load/bff-load-test.jmx`     | JMeter test plan with OAuth2 token acquisition  |
| `tests/load/load-test-config.yaml` | Azure Load Testing YAML configuration           |
| `.github/workflows/load-test.yml`  | GitHub Actions workflow for automated execution |

## FAQ

### Do I need new BFF container environment variables?

**No.** The load test client credentials are only used by JMeter (running in Azure Load Testing engines) to acquire bearer tokens from Entra ID. The BFF validates these tokens using its existing configuration (`BFF_ENTRA_TENANT_ID`, `BFF_ENTRA_CLIENT_ID`, `BFF_ENTRA_AUDIENCE`). No changes to the BFF deployment or `deploy-container-apps.sh` are needed.

### Where are the test credentials stored?

| Credential               | Storage Location                      |
| ------------------------ | ------------------------------------- |
| `LOADTEST_CLIENT_ID`     | GitHub environment variable (`vars`)  |
| `LOADTEST_TOKEN_SCOPE`   | GitHub environment variable (`vars`)  |
| `LOADTEST_CLIENT_SECRET` | GitHub environment secret (`secrets`) |

The client secret is passed to Azure Load Testing as a secret parameter, which maps it to a JMeter property that the test plan reads.

### Can I customize the load profile?

Yes. Modify the env vars in the workflow or pass overrides via `workflow_dispatch`:

- `THREAD_COUNT` — concurrent virtual users (default: 10)
- `RAMP_UP_SECONDS` — ramp-up period (default: 30)
- `LOOP_COUNT` — iterations per thread (default: 50)

For higher load, increase `engineInstances` in `load-test-config.yaml` (each engine runs the full thread count).
