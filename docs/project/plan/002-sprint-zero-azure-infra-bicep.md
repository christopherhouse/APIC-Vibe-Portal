# 002 - Sprint Zero: Azure Infrastructure as Code (Bicep)

## References
- [Architecture Document](../apic_architecture.md) — Deployment: Azure Container Apps, ACR, Key Vault; Components: AI Search, OpenAI, App Insights
- [Product Charter](../apic_product_charter.md) — Phased delivery timeline; MVP through Analytics
- [Product Spec](../apic_portal_spec.md) — Feature requirements driving infrastructure needs

## Overview
Establish the Azure infrastructure foundation using Bicep templates. This creates all the Azure resources needed for the APIC Vibe Portal, parameterized for multi-environment deployment (dev, staging, prod).

## Dependencies
- **001** — Repository scaffolding (monorepo structure, `/infra` directory)

## Implementation Details

### 1. Bicep Project Structure
```
/infra/
├── main.bicep              # Orchestrator template
├── main.bicepparam         # Default parameters
├── modules/
│   ├── container-apps-env.bicep    # Container Apps Environment
│   ├── container-app.bicep         # Container App (reusable)
│   ├── acr.bicep                   # Azure Container Registry
│   ├── key-vault.bicep             # Key Vault
│   ├── api-center.bicep            # Azure API Center
│   ├── ai-search.bicep             # Azure AI Search
│   ├── openai.bicep                # Azure OpenAI
│   ├── app-insights.bicep          # Application Insights + Log Analytics
│   ├── managed-identity.bicep      # User-assigned managed identity
│   └── entra-config.bicep          # Entra ID app registration config
└── env/
    ├── dev.bicepparam
    ├── staging.bicepparam
    └── prod.bicepparam
```

### 2. Core Resources (main.bicep)
The orchestrator template should deploy the following modules in dependency order:

1. **Resource Group** (or target an existing one via parameter)
2. **User-Assigned Managed Identity** — Used by Container Apps to access other services
3. **Log Analytics Workspace + Application Insights** — Observability foundation
4. **Key Vault** — Secrets management; grant managed identity access
5. **Azure Container Registry** — Docker image storage
6. **Container Apps Environment** — Linked to Log Analytics
7. **Azure API Center** — The API catalog data source
8. **Azure AI Search** — Search service for hybrid retrieval
9. **Azure OpenAI** — GPT model deployment for AI features
10. **Container App (Frontend)** — Next.js app, initially with placeholder image
11. **Container App (BFF)** — BFF API, initially with placeholder image

### 3. Parameterization
- Environment name (dev/staging/prod)
- Resource name prefix/suffix
- SKU tiers (allow cheaper SKUs for dev)
- Azure region
- Container image tags (default to placeholder)
- Entra ID tenant and app registration IDs

### 4. Security Configuration
- Key Vault: managed identity has `get` and `list` on secrets
- ACR: managed identity has `AcrPull` role
- AI Search: managed identity has `Search Index Data Reader`
- OpenAI: managed identity has `Cognitive Services OpenAI User`
- API Center: managed identity has `Azure API Center Data Reader`
- All resources use private endpoints where supported (parameterized, optional for dev)

### 5. Outputs
The main template should output:
- Container App URLs (frontend, BFF)
- ACR login server
- Key Vault URI
- AI Search endpoint
- OpenAI endpoint
- API Center endpoint
- Application Insights connection string

## Testing & Acceptance Criteria
- [ ] `az bicep build --file infra/main.bicep` succeeds with no errors
- [ ] All modules compile independently
- [ ] Parameter files for dev, staging, and prod are valid
- [ ] Template deploys successfully to a test resource group (manual validation)
- [ ] Managed identity has correct role assignments for each resource
- [ ] Outputs are correctly defined and populated after deployment
- [ ] No secrets are hardcoded; all sensitive values reference Key Vault or parameters

## Coding Agent Prompt

> **Task**: Implement plan step 002 — Azure Infrastructure as Code (Bicep).
>
> Read the full task specification at `docs/project/plan/002-sprint-zero-azure-infra-bicep.md`.
>
> Reference the architecture at `docs/project/apic_architecture.md` for the full list of Azure services: Container Apps, ACR, Key Vault, API Center, AI Search, Azure OpenAI, Application Insights.
>
> Create the Bicep template structure under `/infra/` with a main orchestrator and individual modules for each Azure resource. Include parameterization for multi-environment deployment (dev, staging, prod). Configure managed identity with appropriate RBAC role assignments for each service. Include all outputs needed by the CI/CD pipeline (task 003).
>
> Validate the templates compile with `az bicep build --file infra/main.bicep`. Do NOT actually deploy to Azure.
