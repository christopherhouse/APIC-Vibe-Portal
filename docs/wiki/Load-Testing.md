# Load Testing

## Overview

Load testing is implemented using **Azure Load Testing** with a JMeter test plan. Tests run against the BFF API with OAuth 2.0 bearer tokens.

## Components

| Component                   | Location                           | Description                                   |
| --------------------------- | ---------------------------------- | --------------------------------------------- |
| Azure Load Testing resource | `infra/modules/load-testing.bicep` | Azure-managed JMeter engine                   |
| JMeter test plan            | `tests/load/bff-load-test.jmx`     | Test scenarios and HTTP requests              |
| Load test config            | `tests/load/load-test-config.yaml` | Azure Load Testing YAML with failure criteria |
| GitHub Actions workflow     | `.github/workflows/load-test.yml`  | Automates test execution                      |

## Architecture

```
GitHub Actions (load-test.yml)
  │
  ▼
Azure Load Testing (JMeter engines)
  │  1. Acquire OAuth token (client_credentials)
  │     using LOADTEST_CLIENT_ID + LOADTEST_CLIENT_SECRET
  ▼
BFF Container App (target)
  │  Bearer token validated by BFF JWT middleware
  ▼
Response
```

> **Important**: The load test service principal credentials are used **only by JMeter** to acquire tokens. No new BFF environment variables are needed — the BFF validates tokens with its existing Entra configuration.

## Setup

### 1. Deploy Infrastructure

The Azure Load Testing resource is deployed via Bicep:

```bash
az deployment group create \
  --resource-group <rg-name> \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam
```

### 2. Create Load Test Service Principal

Create a dedicated service principal for token acquisition during load tests:

```bash
az ad sp create-for-rbac --name "apic-portal-load-test-sp" --skip-assignment
# Note the appId (client ID) and password (client secret)
```

### 3. Configure GitHub Secrets & Variables

| Type                 | Name                     | Value                            |
| -------------------- | ------------------------ | -------------------------------- |
| Environment variable | `LOADTEST_CLIENT_ID`     | Load test SP client ID           |
| Environment variable | `LOADTEST_TOKEN_SCOPE`   | `api://<bff-client-id>/.default` |
| Environment secret   | `LOADTEST_CLIENT_SECRET` | Load test SP client secret       |

### 4. Trigger

The workflow triggers automatically after a successful `Deploy Application` run on `main`, or manually via `workflow_dispatch`.

## Failure Criteria

The load test YAML defines failure criteria that fail the workflow if exceeded:

| Metric                | Threshold |
| --------------------- | --------- |
| Average response time | < 2000ms  |
| Error rate            | < 5%      |
| P95 response time     | < 5000ms  |

## Related

- [[CI-CD Pipeline]] — Load test in the full pipeline context
- `docs/LOAD-TESTING.md` — Full setup guide
