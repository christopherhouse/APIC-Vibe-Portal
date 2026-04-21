# Troubleshooting Guide

Common issues and their solutions for the APIC Vibe Portal AI.

## Frontend Issues

### Portal shows blank page or loading indefinitely

**Symptoms**: The page loads but shows a spinner that never goes away.

**Diagnosis**:

1. Open browser DevTools → Console tab — look for JavaScript errors
2. Open Network tab — check if API calls are failing (red requests)
3. Check Application Insights for uncaught exceptions

**Solutions**:

- If BFF calls are failing with CORS errors: verify the BFF Container App's allowed origins setting
- If auth fails: check that the Entra ID app registration is still valid and the redirect URI is correct
- If the frontend cannot reach the BFF: verify `BFF_URL` (server-side env var) is set correctly on the frontend Container App

---

### "Sign in" button does not work

**Symptoms**: Clicking Sign in does nothing, or the auth flow fails.

**Diagnosis**:

1. Check browser console for MSAL errors
2. Verify `MSAL_CLIENT_ID`, `MSAL_AUTHORITY`, and `MSAL_REDIRECT_URI` are set correctly on the frontend Container App
3. Check that the redirect URI matches what is registered in the app registration

**Solutions**:

- Ensure the redirect URI in `.env` matches the URI registered in Azure Entra ID
- If using a custom domain, add it to the app registration redirect URIs
- Check if the user's account is in the correct tenant

---

### API catalog shows "Failed to load APIs"

**Symptoms**: Catalog page shows an error state instead of API cards.

**Diagnosis**:

1. Check the BFF health endpoint: `GET <bff-url>/health`
2. Look at BFF logs: `az containerapp logs show --name <bff-app> --resource-group <rg>`
3. Check Application Insights for recent BFF exceptions

**Solutions**:

- If BFF is down: restart the Container App or roll back to previous revision
- If API Center connection fails: verify `API_CENTER_*` environment variables
- If authentication to API Center fails: check the managed identity assignment

---

## BFF API Issues

### BFF returns 500 errors

**Symptoms**: All API calls fail with HTTP 500.

**Diagnosis**:

```bash
# View live BFF logs
az containerapp logs show \
  --name <bff-app> \
  --resource-group <rg> \
  --follow

# Check recent exceptions in Application Insights
# KQL: exceptions | where timestamp > ago(1h) | order by timestamp desc | take 20
```

**Solutions**:

- Look for the Python traceback in the logs — it usually identifies the root cause
- Missing environment variable: add it to Container App secrets/environment
- Azure service connection failure: check the endpoint URLs and credentials

---

### AI chat returns no response or times out

**Symptoms**: Users send a chat message and receive no response, or the response times out after ~30 seconds.

**Diagnosis**:

1. Check BFF logs for OpenAI or Foundry Agent errors
2. Check Azure OpenAI Studio for quota usage — may have hit TPM limits
3. Check Foundry Agent Service status

**Solutions**:

- **TPM exceeded**: Increase the TPM quota in Azure OpenAI Studio or wait for the quota window to reset
- **Foundry Agent connection failure**: Verify `AZURE_FOUNDRY_*` environment variables
- **Network timeout**: Check if Container App has network access to Azure OpenAI endpoint (private endpoints)

---

### Search returns no results

**Symptoms**: All searches return empty results.

**Diagnosis**:

1. Check if the AI Search index is populated: go to Azure Portal → AI Search → Indexes → check document count
2. Check BFF logs for search errors
3. Verify `AZURE_SEARCH_ENDPOINT` and `AZURE_SEARCH_KEY` are correct

**Solutions**:

- If index is empty: re-run the indexer (`cd src/indexer && uv run python main.py`)
- If search key is invalid: rotate the key in Azure AI Search and update the BFF environment variable

---

## Infrastructure Issues

### Container App restarts frequently

**Symptoms**: Azure Monitor shows frequent container restarts; users experience brief outages.

**Diagnosis**:

1. Check Container App logs for crash reasons
2. Check CPU and memory metrics — app may be OOM-killed

**Solutions**:

- **Out of Memory**: Increase the Container App's resource allocation
  ```bash
  az containerapp update \
    --name <app-name> \
    --resource-group <rg> \
    --cpu 1.0 \
    --memory 2.0Gi
  ```
- **Crash loop**: Check logs for Python exceptions; roll back if caused by a bad deployment

---

### Cosmos DB "Request rate is large" errors

**Symptoms**: BFF logs show `429 Too Many Requests` from Cosmos DB.

**Solutions**:

- For serverless accounts: you are within the limit but experiencing bursting — add retry logic (already in the SDK)
- For provisioned accounts: increase RU/s on the affected container
- Check for unintended full-table scans in the code — add appropriate indexes

---

## Diagnostic Commands

```bash
# Check Container App health
az containerapp show \
  --name <app-name> \
  --resource-group <rg> \
  --query "properties.{runningStatus:runningStatus,latestRevision:latestRevisionName}"

# Get Container App environment variables
az containerapp show \
  --name <app-name> \
  --resource-group <rg> \
  --query "properties.template.containers[0].env"

# View recent logs (last 50 lines)
az containerapp logs show \
  --name <app-name> \
  --resource-group <rg> \
  --tail 50

# Check AI Search index document count
az search index show \
  --service-name <search-service> \
  --name <index-name> \
  --resource-group <rg> \
  --query statistics
```

## Related Documentation

- **[Monitoring Runbook](monitoring-runbook.md)**
- **[Incident Response](incident-response.md)**
- **[Deployment Guide](deployment-guide.md)**
- **[Backup and Recovery](backup-recovery.md)**
