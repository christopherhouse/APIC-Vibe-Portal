# Scaling Guide

This guide describes how to scale the APIC Vibe Portal AI on Azure Container Apps to handle increased load.

## Auto-Scaling Configuration

Both Container Apps are configured with HTTP-based auto-scaling rules. The default configuration is:

| Setting             | Frontend               | BFF                    |
| ------------------- | ---------------------- | ---------------------- |
| Minimum replicas    | 1                      | 1                      |
| Maximum replicas    | 10                     | 10                     |
| Scale trigger       | HTTP requests / second | HTTP requests / second |
| Scale-out threshold | 100 req/s per replica  | 50 req/s per replica   |

> **Note**: Minimum replicas set to 1 ensures there is always at least one instance available, avoiding cold-start delays.

## Viewing Current Scale Status

```bash
# View replica count for frontend
az containerapp revision show \
  --name <frontend-app> \
  --resource-group <rg> \
  --revision <current-revision> \
  --query properties.replicas

# List all active revisions
az containerapp revision list \
  --name <frontend-app> \
  --resource-group <rg> \
  --query "[].{name:name, replicas:properties.replicas, active:properties.active}"
```

## Updating Auto-Scale Rules

To adjust the HTTP scale trigger threshold:

```bash
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --scale-rule-name http-scale \
  --scale-rule-type http \
  --scale-rule-http-concurrency 80
```

To adjust min/max replicas:

```bash
az containerapp update \
  --name <app-name> \
  --resource-group <rg> \
  --min-replicas 2 \
  --max-replicas 20
```

## Manual Scaling

If auto-scaling is insufficient for a known high-traffic period (e.g., a company-wide launch event):

```bash
# Pre-scale the BFF to 5 replicas
az containerapp update \
  --name <bff-app> \
  --resource-group <rg> \
  --min-replicas 5
```

Remember to reduce after the event:

```bash
az containerapp update \
  --name <bff-app> \
  --resource-group <rg> \
  --min-replicas 1
```

## Scaling Downstream Services

When scaling the portal, also consider scaling these dependent services:

### Azure Cosmos DB

Cosmos DB in serverless mode scales automatically. For predictable high traffic, consider switching to provisioned throughput and increasing RUs.

```bash
# Check current consumption
az cosmosdb sql database throughput show \
  --account-name <cosmos-account> \
  --resource-group <rg> \
  --name <database-name>
```

### Azure AI Search

AI Search scales by adding replicas:

```bash
az search service update \
  --name <search-service> \
  --resource-group <rg> \
  --replica-count 3
```

### Azure OpenAI

OpenAI token limits are set at the deployment level. If you hit TPM (tokens per minute) limits:

1. Go to **Azure OpenAI Studio** → Deployments
2. Select the deployment and adjust the TPM quota

## Load Testing

Before a major launch, run load tests to validate scaling behaviour. See `load-tests/` directory for k6 load test scripts.

```bash
# Run the load test (requires k6 installed)
k6 run load-tests/catalog-load.js \
  --env BASE_URL=https://<frontend-url>
```

Target thresholds:

- 95th percentile response time < 2 s under 500 concurrent users
- Error rate < 1% at peak load

## Cost Considerations

- **Container Apps**: Billing is based on vCPU-seconds and memory GB-seconds consumed. Auto-scaling helps optimize costs.
- **Cosmos DB serverless**: Billing per RU consumed — no idle cost.
- **Azure OpenAI**: Billing per 1,000 tokens. Monitor consumption with Application Insights custom events.
- **AI Search**: Billing per search unit (SU). Adding replicas increases cost proportionally.

## Related Documentation

- **[Deployment Guide](deployment-guide.md)**
- **[Monitoring Runbook](monitoring-runbook.md)**
- **[Backup and Recovery](backup-recovery.md)**
