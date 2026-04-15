# APIC Vibe Portal - Azure Infrastructure

This directory contains Bicep templates for deploying the APIC Vibe Portal AI infrastructure to Azure.

## Architecture

The infrastructure includes:

- **Observability**: Log Analytics Workspace + Application Insights
- **Identity**: User-assigned managed identity with RBAC
- **Secrets**: Azure Key Vault (RBAC-enabled)
- **Containers**: Azure Container Registry + Container Apps Environment
- **API Catalog**: Azure API Center
- **Search**: Azure AI Search (hybrid search with semantic ranking)
- **AI Services**: Azure OpenAI (AIServices kind)
- **Persistence**: Azure Cosmos DB (serverless NoSQL)
- **Agent Platform**: Azure AI Foundry Agent Service

## Directory Structure

```
/infra/
├── main.bicep              # Main orchestrator template
├── modules/                # Individual resource modules
│   ├── monitoring.bicep
│   ├── managed-identity.bicep
│   ├── key-vault.bicep
│   ├── acr.bicep
│   ├── container-apps-env.bicep
│   ├── api-center.bicep
│   ├── ai-search.bicep
│   ├── openai.bicep
│   ├── cosmosdb.bicep
│   └── foundry-agent.bicep
└── env/                    # Environment-specific parameters
    ├── dev.bicepparam
    ├── staging.bicepparam
    └── prod.bicepparam
```

## Prerequisites

- Azure CLI (`az`) version 2.50.0 or later
- Bicep CLI (automatically installed with Azure CLI)
- Azure subscription with appropriate permissions
- (For production) VNet and subnet for private endpoints

## Usage

### 1. Validate Templates

```bash
# Validate main template
az bicep build --file infra/main.bicep

# Validate all modules
for file in infra/modules/*.bicep; do
  echo "Validating $file..."
  az bicep build --file "$file"
done
```

### 2. Deploy to Azure

**Important**: Container Apps are NOT deployed via Bicep. Deploy them separately via bash script after infrastructure provisioning and container image push to ACR.

#### Deploy to Dev Environment

```bash
# Create resource group
az group create \
  --name rg-apicvibe-dev \
  --location eastus

# Deploy infrastructure
az deployment group create \
  --resource-group rg-apicvibe-dev \
  --template-file infra/main.bicep \
  --parameters infra/env/dev.bicepparam
```

#### Deploy to Staging Environment

```bash
# Create resource group
az group create \
  --name rg-apicvibe-staging \
  --location eastus

# Deploy infrastructure
az deployment group create \
  --resource-group rg-apicvibe-staging \
  --template-file infra/main.bicep \
  --parameters infra/env/staging.bicepparam
```

#### Deploy to Production Environment

```bash
# Create resource group
az group create \
  --name rg-apicvibe-prod \
  --location eastus

# IMPORTANT: Update prod.bicepparam with actual subnet ID for private endpoints

# Deploy infrastructure
az deployment group create \
  --resource-group rg-apicvibe-prod \
  --template-file infra/main.bicep \
  --parameters infra/env/prod.bicepparam
```

### 3. Deploy Container Apps (Separate Step)

After infrastructure is provisioned and container images are pushed to ACR, deploy Container Apps via bash script:

```bash
# This will be implemented in task 003 (CI/CD pipeline)
./scripts/deploy-container-apps.sh --environment dev
```

## Configuration

### Environment Parameters

Each environment has a `.bicepparam` file under `/infra/env/` that configures:

- **Environment name**: dev, staging, prod
- **SKU tiers**: Cheaper SKUs for dev, premium for prod
- **Private endpoints**: Disabled in dev, enabled in prod
- **Cosmos DB regions**: Single-region for dev/staging, multi-region for prod
- **Container images**: Placeholder for initial deployment, actual images from ACR for prod

### Customization

To customize the deployment:

1. Edit the appropriate `.bicepparam` file under `/infra/env/`
2. Update parameter values (SKUs, regions, etc.)
3. Redeploy using `az deployment group create`

### Private Endpoints

For production deployments with private endpoints:

1. Provision a VNet and subnet first
2. Update `prod.bicepparam` with the subnet resource ID
3. Deploy infrastructure with `enablePrivateEndpoints = true`

## Security

- **RBAC**: All resources use Azure RBAC (no access keys)
- **Managed Identity**: Single user-assigned identity with least-privilege roles
- **Key Vault**: RBAC-enabled, soft delete + purge protection
- **Diagnostic Settings**: All resources send logs to Log Analytics
- **Private Endpoints**: Available for prod (Key Vault, ACR, AI Search, OpenAI, Cosmos DB)

### Role Assignments

The managed identity is granted:

- **Key Vault Secrets User** on Key Vault
- **AcrPull** on Container Registry
- **Azure API Center Data Reader** on API Center
- **Search Index Data Reader** on AI Search
- **Search Service Contributor** on AI Search
- **Cognitive Services OpenAI User** on Azure OpenAI
- **Cognitive Services User** on Foundry Agent Service
- **Cosmos DB Built-in Data Contributor** on Cosmos DB

## Foundry Agent Service

The Foundry Agent Service module provisions:

- **AI Services Account** (kind: `AIServices`)
- **Foundry Project** attached to the account
- **Capability Hosts** for Standard Agent Services (account + project level)
- **RBAC** for managed identity access

This setup enables multi-agent orchestration for governance and compliance agents (Phase 2, Task 022).

## Observability

All Azure resources have diagnostic settings configured to send logs and metrics to the Log Analytics workspace.

Query logs in Azure Portal:

1. Navigate to Log Analytics Workspace
2. Use Kusto Query Language (KQL) to query logs
3. Example: `AzureDiagnostics | where ResourceProvider == "MICROSOFT.COGNITIVESERVICES" | take 100`

## Outputs

After deployment, the following outputs are available:

- ACR login server
- Key Vault URI
- AI Search endpoint
- OpenAI endpoint
- API Center endpoint
- Foundry Agent Service endpoint
- Cosmos DB endpoint
- Application Insights connection string
- Container Apps Environment ID (for subsequent app deployment)

Retrieve outputs:

```bash
az deployment group show \
  --resource-group rg-apicvibe-dev \
  --name <deployment-name> \
  --query properties.outputs
```

## Troubleshooting

### Bicep Compilation Errors

```bash
# Build and check for errors
az bicep build --file infra/main.bicep
```

### Deployment Failures

```bash
# Check deployment status
az deployment group show \
  --resource-group rg-apicvibe-dev \
  --name <deployment-name>

# View deployment operations
az deployment operation group list \
  --resource-group rg-apicvibe-dev \
  --name <deployment-name>
```

### Resource Naming Conflicts

If you encounter naming conflicts (e.g., globally unique names already taken):

- Update `uniqueSuffix` parameter in main.bicep
- Or modify `namePrefix` in the parameter file

## Notes

- **No Container App Bicep modules**: Per project conventions, Container Apps are deployed via bash script AFTER infrastructure provisioning, not via Bicep
- **Cosmos DB Serverless**: Using serverless capacity mode (no provisioned throughput)
- **Foundry Agents**: Agent configuration is handled in Task 022, not here
- **Entra ID**: Authentication setup is handled in Task 016
- **Azure Verified Modules**: This template follows AVM patterns where practical

## References

- [Azure Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/)
- [Architecture Document](../docs/project/apic_architecture.md)
- [Implementation Plan](../docs/project/plan/002-sprint-zero-azure-infra-bicep.md)
