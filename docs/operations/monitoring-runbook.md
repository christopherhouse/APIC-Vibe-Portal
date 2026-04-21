# Monitoring Runbook

This runbook describes how to monitor the APIC Vibe Portal AI in production using **Azure Application Insights** and **Azure Monitor**.

## Monitoring Stack

| Tool                       | Purpose                                                       |
| -------------------------- | ------------------------------------------------------------- |
| Azure Application Insights | Frontend and BFF telemetry, traces, custom events             |
| Azure Monitor              | Infrastructure metrics (Container Apps, Cosmos DB, AI Search) |
| Azure Log Analytics        | Centralized log aggregation and querying                      |
| Azure Monitor Alerts       | Automated alerting on threshold violations                    |

## Key Metrics

### Frontend (Next.js)

| Metric                | Description                 | Target           |
| --------------------- | --------------------------- | ---------------- |
| Page load time (P95)  | 95th percentile page load   | < 2 s            |
| JavaScript exceptions | Uncaught client-side errors | 0 per hour       |
| MSAL auth failures    | Entra ID sign-in failures   | < 1% of attempts |

### BFF (FastAPI)

| Metric         | Description                   | Target           |
| -------------- | ----------------------------- | ---------------- |
| Request rate   | Requests per second           | —                |
| Error rate     | 5xx responses / total         | < 1%             |
| Latency (P95)  | 95th percentile response time | < 500 ms         |
| AI token usage | OpenAI tokens consumed        | Monitor for cost |

### Infrastructure

| Resource                 | Key Metric                    | Alert Threshold   |
| ------------------------ | ----------------------------- | ----------------- |
| Container App (Frontend) | CPU utilization               | > 80% for 5 min   |
| Container App (BFF)      | CPU utilization               | > 80% for 5 min   |
| Container App (BFF)      | Memory utilization            | > 85% for 5 min   |
| Cosmos DB                | Request unit (RU) consumption | > 80% provisioned |
| AI Search                | Query latency (P99)           | > 1 s             |

## Alert Rules

The following alert rules should be configured in Azure Monitor:

### Error Rate Alerts

```
Signal: requests/failed
Condition: Count > [threshold] per 5 minutes
Severity 2 (Warning): threshold = requests * 5%
Severity 1 (Critical): threshold = requests * 10%
```

### Response Time Alerts

```
Signal: requests/duration (P95)
Condition: Value > 2000 ms
Severity 2 (Warning)
```

### Availability Alert

```
Signal: availabilityResults/availabilityPercentage
Condition: Value < 99.5%
Severity 1 (Critical)
```

### Container App Restart Alert

```
Signal: RestartCount
Condition: Count > 3 per 15 minutes
Severity 2 (Warning)
```

## Dashboards

Import the pre-built dashboard from `infra/monitoring/dashboard.json` (if available) into the Azure Portal for a unified operational view.

Alternatively, create a custom dashboard with these tiles:

1. **Availability** — Availability test success rate (last 24h)
2. **Error rate** — Failed requests per minute
3. **Latency P95** — 95th percentile response time
4. **Active users** — Active sessions
5. **AI token usage** — OpenAI token consumption per hour
6. **Container App health** — CPU and memory for both apps

## Log Queries (KQL)

### Find all 500 errors in the last hour

```kusto
requests
| where timestamp > ago(1h)
| where resultCode == "500"
| project timestamp, name, url, resultCode, duration, operation_Id
| order by timestamp desc
```

### AI chat errors

```kusto
exceptions
| where timestamp > ago(1h)
| where operation_Name contains "chat"
| project timestamp, type, outerMessage, operation_Id
| order by timestamp desc
```

### Slow requests (P95 > 2s)

```kusto
requests
| where timestamp > ago(1h)
| where duration > 2000
| project timestamp, name, url, duration, operation_Id
| order by duration desc
| take 50
```

### Authentication failures

```kusto
customEvents
| where timestamp > ago(1h)
| where name == "AuthFailure"
| project timestamp, customDimensions
| order by timestamp desc
```

## On-Call Response

### Severity 1 (Critical) — Immediate Response Required

1. Check Azure Portal → Application Insights → Live Metrics for real-time view
2. Run KQL query to identify the failing component
3. Check Container App health: `az containerapp show --name <app> --resource-group <rg>`
4. If a container is crash-looping, roll back to the previous revision (see [Deployment Guide](deployment-guide.md))
5. Page the on-call engineer if the issue is not resolved within 15 minutes
6. Open an incident in the incident tracking system
7. Post a status update in the team Slack channel

### Severity 2 (Warning) — Respond Within 4 Hours

1. Acknowledge the alert in Azure Monitor
2. Investigate using KQL queries above
3. Create a follow-up issue if the cause is identified but not urgent
4. Resolve within the next business day if not a production blocker

## Related Documentation

- **[Incident Response](incident-response.md)**
- **[Scaling Guide](scaling-guide.md)**
- **[Troubleshooting](troubleshooting.md)**
