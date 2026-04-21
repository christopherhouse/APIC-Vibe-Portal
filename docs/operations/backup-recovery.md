# Backup and Recovery

This document describes the backup strategy and recovery procedures for the APIC Vibe Portal AI.

## Data Inventory

| Data Store                | Contents                                              | Recovery Criticality                      |
| ------------------------- | ----------------------------------------------------- | ----------------------------------------- |
| **Azure API Center**      | API definitions, versions, deployments, environments  | High — source of truth for catalog        |
| **Azure Cosmos DB**       | Chat sessions, governance snapshots, analytics events | Medium — losing recent data is acceptable |
| **Azure AI Search Index** | Indexed API metadata (derived from API Center)        | Low — can be rebuilt from API Center      |
| **Application Insights**  | Telemetry, traces, logs                               | Low — historical data only                |

## Backup Strategy

### Azure API Center

API Center data is managed by the Azure platform. Microsoft provides built-in geo-redundancy.

**Additional recommendation**: Export API definitions to a Git repository or storage account regularly.

```bash
# Export all API definitions using Azure CLI
az apic api list \
  --service-name <apic-service> \
  --resource-group <rg> \
  --output json > backup/api-center-$(date +%Y%m%d).json
```

### Azure Cosmos DB

Configure continuous backup (point-in-time restore) in the Cosmos DB account:

```bash
az cosmosdb update \
  --name <cosmos-account> \
  --resource-group <rg> \
  --backup-policy-type Continuous \
  --continuous-tier Continuous7Days
```

This provides point-in-time restore up to 7 days back.

**Manual backup** (run weekly via Azure Automation or GitHub Actions scheduled workflow):

```bash
az cosmosdb sql container show \
  --account-name <cosmos-account> \
  --database-name <db-name> \
  --name <container-name> \
  --resource-group <rg>
```

Use Azure Data Factory or a custom script to export container data to Azure Blob Storage.

### Azure AI Search Index

The search index is derived from Azure API Center data. It can be fully rebuilt by re-running the indexing pipeline:

```bash
# Trigger index rebuild via the BFF indexer
cd src/indexer
uv run python main.py --full-rebuild
```

This is not a backup item — it is a derived data store.

### Application Configuration

Store all environment-specific configuration in Azure Key Vault. The Key Vault itself has soft-delete enabled by default (90-day recovery window).

```bash
# Verify soft-delete is enabled
az keyvault show \
  --name <keyvault-name> \
  --resource-group <rg> \
  --query properties.enableSoftDelete
```

## Recovery Procedures

### Recover Lost Chat Sessions (Cosmos DB)

If chat session data was accidentally deleted:

1. Go to **Azure Portal → Cosmos DB → <account> → Point In Time Restore**
2. Select the restore timestamp (before the deletion)
3. Create a new Cosmos DB account from the restore
4. Copy the required data back to the original account (or update the BFF connection string to point to the restored account)

### Rebuild AI Search Index

If the search index is corrupted or empty:

```bash
# Delete the existing index
az search index delete \
  --service-name <search-service> \
  --name <index-name> \
  --resource-group <rg>

# Re-run the indexer
cd src/indexer
uv run python main.py --full-rebuild
```

The index rebuild typically takes 5–30 minutes depending on catalog size.

### Restore from API Center Backup

If API definitions were accidentally deleted from API Center:

1. Locate the most recent JSON export from the backup storage account
2. Use the Azure API Center REST API or CLI to re-import definitions
3. Trigger a full AI Search index rebuild after restoration

### Disaster Recovery (Full Environment)

If the entire Azure environment is lost:

1. **Provision infrastructure** using Bicep templates: see [Deployment Guide](deployment-guide.md)
2. **Restore Cosmos DB** from continuous backup to a new account
3. **Import API definitions** from the most recent JSON export backup
4. **Rebuild AI Search index** using the indexer
5. **Deploy container images** from ACR (or rebuild from source if ACR is also lost)
6. **Update DNS** to point to the new Container App URLs

**RTO (Recovery Time Objective)**: 4 hours  
**RPO (Recovery Point Objective)**: 24 hours (based on daily backup schedule)

## Testing Recovery Procedures

Recovery procedures should be tested quarterly:

1. **Cosmos DB restore test**: Restore to a non-production environment and verify data integrity
2. **Index rebuild test**: Delete and rebuild the index in a staging environment; verify search works
3. **Full DR drill**: Once a year, provision a new environment from scratch using the procedures above

Document the results of each test in the team wiki.

## Related Documentation

- **[Deployment Guide](deployment-guide.md)**
- **[Monitoring Runbook](monitoring-runbook.md)**
- **[Incident Response](incident-response.md)**
- **[Scaling Guide](scaling-guide.md)**
