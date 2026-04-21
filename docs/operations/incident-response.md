# Incident Response

This document describes the procedures for handling production incidents affecting the APIC Vibe Portal AI.

## Incident Severity Levels

| Severity          | Description                                               | Response Time     | Resolution Target |
| ----------------- | --------------------------------------------------------- | ----------------- | ----------------- |
| **S1 — Critical** | Portal is completely unavailable or data breach suspected | 15 minutes        | 2 hours           |
| **S2 — High**     | Major feature broken (e.g., AI chat non-functional)       | 1 hour            | 4 hours           |
| **S3 — Medium**   | Degraded performance or minor feature issue               | 4 hours           | Next business day |
| **S4 — Low**      | Cosmetic issue, minor UX problem                          | Next business day | Next sprint       |

## Incident Response Process

### 1. Detect

Incidents are detected via:

- Azure Monitor alerts (see [Monitoring Runbook](monitoring-runbook.md))
- User-reported issues via support channels
- Proactive health checks in CI/CD pipeline

### 2. Acknowledge

- Acknowledge the alert in Azure Monitor within the response time target
- Post in the team Slack channel: `#portal-incidents`
  ```
  🚨 Incident OPEN — [brief description]
  Severity: S[N]
  Investigating by: @your-name
  Started: [timestamp]
  ```

### 3. Assess

Perform an initial assessment:

1. **What is the impact?** — How many users are affected? Which features?
2. **When did it start?** — Check Application Insights for the timestamp of first failure
3. **What changed recently?** — Check recent deployments in GitHub Actions or Azure Portal
4. **Is it isolated?** — Is it one region, one user, one feature, or global?

### 4. Mitigate

Apply a mitigation action based on the root cause:

#### Portal is down (no response)

```bash
# Check Container App status
az containerapp show --name <frontend-app> --resource-group <rg> \
  --query properties.runningStatus

# Check recent revisions
az containerapp revision list --name <frontend-app> --resource-group <rg>

# Rollback if recent deployment caused the issue
az containerapp revision activate \
  --revision <previous-revision-name> \
  --resource-group <rg>
```

#### BFF API errors (5xx)

```bash
# Check BFF logs
az containerapp logs show --name <bff-app> --resource-group <rg> --follow

# Restart the BFF container app
az containerapp revision restart --revision <revision> --resource-group <rg>
```

#### AI Chat non-functional

1. Check Azure OpenAI service status in Azure Portal
2. Check Foundry Agent Service connection settings in BFF environment variables
3. Verify `AZURE_OPENAI_ENDPOINT` and key are still valid

#### Authentication failures

1. Check Entra ID service health at [Azure Status](https://azure.status.microsoft.com/)
2. Verify App Registration hasn't expired
3. Check MSAL configuration in frontend environment variables

### 5. Communicate

Keep stakeholders informed throughout the incident:

- **Users**: If the portal is unavailable, post a status update on the internal status page
- **Team**: Update the Slack channel every 30 minutes for S1/S2 incidents
- **Leadership**: Escalate S1 incidents to engineering leadership within 30 minutes

### 6. Resolve

Once the incident is resolved:

1. Confirm the fix is working (check Application Insights — error rate back to baseline)
2. Post resolution in Slack:
   ```
   ✅ Incident RESOLVED — [brief description of fix]
   Duration: [start time] → [end time]
   Root cause: [1 sentence]
   ```
3. Close the alert in Azure Monitor

### 7. Post-Incident Review (PIR)

For S1 and S2 incidents, complete a PIR within 5 business days:

1. Timeline of events
2. Root cause analysis (5 Whys or Fishbone diagram)
3. Impact assessment (users affected, duration)
4. Action items to prevent recurrence
5. Share the PIR document with the team

## Contact Matrix

| Role                     | Contact                | For                                  |
| ------------------------ | ---------------------- | ------------------------------------ |
| On-call engineer         | See PagerDuty rotation | All S1/S2 incidents                  |
| Azure subscription owner | See team wiki          | Subscription quota or billing issues |
| Entra ID admin           | See team wiki          | Authentication/authorization issues  |
| Azure OpenAI team        | Azure Support          | OpenAI service outages               |

## Related Documentation

- **[Monitoring Runbook](monitoring-runbook.md)**
- **[Deployment Guide](deployment-guide.md)**
- **[Backup and Recovery](backup-recovery.md)**
- **[Troubleshooting](troubleshooting.md)**
