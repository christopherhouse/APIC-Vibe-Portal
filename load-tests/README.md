# Load Testing — APIC Vibe Portal

> **Note:** JMeter test plans and the Azure Load Testing configuration live in
> [`tests/load/`](../tests/load/), not this directory.
> This directory is intentionally empty.

## Overview

Load tests run automatically via [Azure Load Testing](https://learn.microsoft.com/azure/load-testing/)
after every successful deployment to `main`, and can be triggered manually for
any environment via the **Load Test (Azure App Testing)** GitHub Actions workflow.

## Files

| File | Purpose |
|------|---------|
| `tests/load/bff-load-test.jmx` | JMeter test plan — three parallel thread groups: catalog browsing (100 VUs), AI search (50 VUs), AI chat (20 VUs) |
| `tests/load/load-test-config.yaml` | Azure Load Testing YAML config — references the JMX, failure criteria, and Key Vault secret URI |

## JWT / Authentication

The JMeter `SetupThreadGroup` acquires a short-lived bearer token from Entra ID
using the **OAuth 2.0 client-credentials** grant before any load threads start.

The client secret is stored in Azure Key Vault (secret name: `loadtest-client-secret`)
and is resolved at test-run time by the ALT managed identity — it is never stored
in plain text in the workflow or source code.

## Required GitHub / Azure configuration

| Item | Where |
|------|-------|
| `LOADTEST_CLIENT_ID` | GitHub Actions repository variable |
| `LOADTEST_TOKEN_SCOPE` | GitHub Actions repository variable (e.g. `api://<bff-client-id>/.default`) |
| `loadtest-client-secret` | Azure Key Vault secret (created out-of-band; ALT identity has `Key Vault Secrets User` role via Bicep) |

## Workflow triggers

- **Automatic:** fires after every successful push-based `Deploy Application` run on `main`
- **Manual:** `workflow_dispatch` on the **Load Test** workflow — choose `dev`, `staging`, or `prod`
