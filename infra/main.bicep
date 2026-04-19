// ============================================================================
// APIC Vibe Portal - Main Infrastructure Orchestrator
// ============================================================================
// This template orchestrates the deployment of all Azure resources for the
// APIC Vibe Portal AI application.
// ============================================================================

targetScope = 'resourceGroup'

// ============================================================================
// PARAMETERS
// ============================================================================

@description('Environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environmentName string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name prefix for all resources')
@minLength(3)
@maxLength(10)
param namePrefix string

@description('Unique suffix for globally unique resource names (defaults to unique string based on resource group)')
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('Entra ID tenant ID')
param entraIdTenantId string = tenant().tenantId

@description('Tags to apply to all resources')
param tags object = {
  Environment: environmentName
  Application: 'APIC-Vibe-Portal'
  ManagedBy: 'Bicep'
  SecurityControl: 'Ignore'
}

// SKU settings (allow cheaper SKUs for dev)
@description('Key Vault SKU')
@allowed(['standard', 'premium'])
param keyVaultSku string = environmentName == 'prod' ? 'premium' : 'standard'

@description('AI Search SKU')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
param aiSearchSku string = environmentName == 'prod' ? 'standard' : 'basic'

@description('Azure OpenAI/AI Services SKU')
@allowed(['S0'])
param openAiSku string = 'S0'

@description('Cosmos DB failover locations (empty for single-region serverless)')
param cosmosDbLocations array = []

@description('Azure region for Cosmos DB (defaults to main location if not specified)')
param cosmosDbLocation string = location

@description('Azure Cache for Redis SKU name (Basic for dev/staging, Standard for prod)')
@allowed(['Basic', 'Standard', 'Premium'])
param redisSku string = environmentName == 'prod' ? 'Standard' : 'Basic'

@description('Azure Cache for Redis SKU family (C = Basic/Standard, P = Premium)')
@allowed(['C', 'P'])
param redisFamily string = 'C'

@description('Azure Cache for Redis capacity (0 = smallest for dev, 1 for prod)')
param redisCapacity int = environmentName == 'prod' ? 1 : 0

@description('Enable private endpoints for resources (recommended for prod)')
param enablePrivateEndpoints bool = environmentName == 'prod'

@description('Subnet resource ID for private endpoints (required if enablePrivateEndpoints is true)')
param privateEndpointSubnetId string = ''

// Note: When enablePrivateEndpoints is true, privateEndpointSubnetId must not be empty.
// This validation is enforced at deployment time by the individual modules.

// ============================================================================
// VARIABLES
// ============================================================================

// Key Vault and Storage Account have strict 24-char limits
// Format: prefix + env (first letter) + suffix (e.g., 'apicvibekd' + suffix = 23 chars max)
var kvPrefix = '${namePrefix}kv${substring(environmentName, 0, 1)}' // e.g., 'apicvibekd' (10 chars)
var kvSuffix = substring(uniqueSuffix, 0, 13) // Use first 13 chars of suffix

var resourceNames = {
  logAnalytics: '${namePrefix}-law-${environmentName}-${uniqueSuffix}'
  appInsights: '${namePrefix}-ai-${environmentName}-${uniqueSuffix}'
  managedIdentity: '${namePrefix}-id-${environmentName}-${uniqueSuffix}'
  frontendIdentity: '${namePrefix}-id-frontend-${environmentName}-${uniqueSuffix}'
  bffIdentity: '${namePrefix}-id-bff-${environmentName}-${uniqueSuffix}'
  indexerIdentity: '${namePrefix}-id-indexer-${environmentName}-${uniqueSuffix}'
  keyVault: '${kvPrefix}${kvSuffix}' // Max 24 chars: 10 (prefix) + 13 (suffix) = 23
  containerRegistry: '${namePrefix}acr${environmentName}${uniqueSuffix}'
  containerAppsEnv: '${namePrefix}-cae-${environmentName}-${uniqueSuffix}'
  frontendApp: '${namePrefix}-frontend-${environmentName}'
  bffApp: '${namePrefix}-bff-${environmentName}'
  apiCenter: '${namePrefix}-apic-${environmentName}-${uniqueSuffix}'
  aiSearch: '${namePrefix}-search-${environmentName}-${uniqueSuffix}'
  openAi: '${namePrefix}-openai-${environmentName}-${uniqueSuffix}'
  cosmosDb: '${namePrefix}-cosmos-${environmentName}-${uniqueSuffix}'
  foundryAccount: '${namePrefix}-foundry-${environmentName}-${uniqueSuffix}'
  foundryProject: '${namePrefix}-project-${environmentName}'
  redisCache: '${namePrefix}-redis-${environmentName}-${uniqueSuffix}'
  loadTest: '${namePrefix}-lt-${environmentName}-${uniqueSuffix}'
}

// ============================================================================
// MODULE 1: Log Analytics Workspace + Application Insights
// ============================================================================

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-${deployment().name}'
  params: {
    location: location
    logAnalyticsName: resourceNames.logAnalytics
    appInsightsName: resourceNames.appInsights
    tags: tags
  }
}

// ============================================================================
// MODULE 2: User-Assigned Managed Identities (per-container)
// ============================================================================

// General-purpose managed identity (backend services RBAC)
module managedIdentity 'modules/managed-identity.bicep' = {
  name: 'managed-identity-${deployment().name}'
  params: {
    location: location
    managedIdentityName: resourceNames.managedIdentity
    tags: tags
  }
}

// Frontend Container App identity (AcrPull only)
module frontendIdentity 'modules/managed-identity.bicep' = {
  name: 'frontend-identity-${deployment().name}'
  params: {
    location: location
    managedIdentityName: resourceNames.frontendIdentity
    tags: tags
  }
}

// BFF Container App identity (AcrPull + backend service access)
module bffIdentity 'modules/managed-identity.bicep' = {
  name: 'bff-identity-${deployment().name}'
  params: {
    location: location
    managedIdentityName: resourceNames.bffIdentity
    tags: tags
  }
}

// Indexer Container Apps Job identity (AcrPull + AI Search write + OpenAI + API Center read)
module indexerIdentity 'modules/managed-identity.bicep' = {
  name: 'indexer-identity-${deployment().name}'
  params: {
    location: location
    managedIdentityName: resourceNames.indexerIdentity
    tags: tags
  }
}

// ============================================================================
// MODULE 3: Key Vault
// ============================================================================

module keyVault 'modules/key-vault.bicep' = {
  name: 'key-vault-${deployment().name}'
  params: {
    location: location
    keyVaultName: resourceNames.keyVault
    sku: keyVaultSku
    tenantId: entraIdTenantId
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    tags: tags
  }
}

// ============================================================================
// MODULE 4: Azure Container Registry
// ============================================================================

module containerRegistry 'modules/acr.bicep' = {
  name: 'acr-${deployment().name}'
  params: {
    location: location
    acrName: resourceNames.containerRegistry
    frontendManagedIdentityPrincipalId: frontendIdentity.outputs.principalId
    bffManagedIdentityPrincipalId: bffIdentity.outputs.principalId
    indexerManagedIdentityPrincipalId: indexerIdentity.outputs.principalId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    tags: tags
  }
}

// ============================================================================
// MODULE 5: Container Apps Environment
// ============================================================================

module containerAppsEnvironment 'modules/container-apps-env.bicep' = {
  name: 'cae-${deployment().name}'
  params: {
    location: location
    containerAppsEnvName: resourceNames.containerAppsEnv
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    tags: tags
  }
}

// ============================================================================
// MODULE 6: Azure API Center
// ============================================================================

module apiCenter 'modules/api-center.bicep' = {
  name: 'api-center-${deployment().name}'
  params: {
    location: location
    apiCenterName: resourceNames.apiCenter
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    indexerManagedIdentityPrincipalId: indexerIdentity.outputs.principalId
    tags: tags
  }
}

// ============================================================================
// MODULE 7: Azure AI Search
// ============================================================================

module aiSearch 'modules/ai-search.bicep' = {
  name: 'ai-search-${deployment().name}'
  params: {
    location: location
    searchServiceName: resourceNames.aiSearch
    sku: aiSearchSku
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    indexerManagedIdentityPrincipalId: indexerIdentity.outputs.principalId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    tags: tags
  }
}

// ============================================================================
// MODULE 8: Azure OpenAI (AI Services)
// ============================================================================

module openAi 'modules/openai.bicep' = {
  name: 'openai-${deployment().name}'
  params: {
    location: location
    openAiName: resourceNames.openAi
    sku: openAiSku
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    indexerManagedIdentityPrincipalId: indexerIdentity.outputs.principalId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    tags: tags
  }
}

// ============================================================================
// MODULE 9: Azure Cosmos DB (Serverless NoSQL)
// ============================================================================

module cosmosDb 'modules/cosmosdb.bicep' = {
  name: 'cosmosdb-${deployment().name}'
  params: {
    location: cosmosDbLocation
    cosmosDbAccountName: resourceNames.cosmosDb
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    additionalLocations: cosmosDbLocations
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    enableZoneRedundancy: environmentName == 'prod'
    tags: tags
  }
}

// ============================================================================
// MODULE 10: Azure AI Foundry Agent Service
// ============================================================================

module foundryAgent 'modules/foundry-agent.bicep' = {
  name: 'foundry-agent-${deployment().name}'
  params: {
    location: location
    foundryAccountName: resourceNames.foundryAccount
    foundryProjectName: resourceNames.foundryProject
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    tags: tags
  }
}

// ============================================================================
// MODULE 11: Azure Cache for Redis
// ============================================================================
// ⚠️  DEPRECATION NOTE: Azure Cache for Redis is deprecated but used here
// because Azure Managed Redis (redisEnterprise) fails to deploy.
// See docs/project/apic_architecture.md for risk acknowledgment.
// ============================================================================

module redisCache 'modules/redis-cache.bicep' = {
  name: 'redis-${deployment().name}'
  params: {
    location: location
    redisCacheName: resourceNames.redisCache
    redisSku: redisSku
    redisFamily: redisFamily
    redisCapacity: redisCapacity
    managedIdentityPrincipalId: bffIdentity.outputs.principalId
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    enablePrivateEndpoint: enablePrivateEndpoints
    privateEndpointSubnetId: privateEndpointSubnetId
    tags: tags
  }
}

// ============================================================================
// MODULE 12: Azure Load Testing (Azure App Testing)
// ============================================================================

module loadTesting 'modules/load-testing.bicep' = {
  name: 'load-testing-${deployment().name}'
  params: {
    location: location
    loadTestName: resourceNames.loadTest
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    tags: tags
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Resource Group name')
output resourceGroupName string = resourceGroup().name

@description('Environment name')
output environmentName string = environmentName

@description('Managed Identity Client ID (general-purpose, backward compatibility)')
output managedIdentityClientId string = managedIdentity.outputs.clientId

@description('Managed Identity Principal ID (general-purpose, backward compatibility)')
output managedIdentityPrincipalId string = managedIdentity.outputs.principalId

@description('Frontend Container App Managed Identity resource ID')
output frontendIdentityResourceId string = frontendIdentity.outputs.id

@description('Frontend Container App Managed Identity Client ID')
output frontendIdentityClientId string = frontendIdentity.outputs.clientId

@description('BFF Container App Managed Identity resource ID')
output bffIdentityResourceId string = bffIdentity.outputs.id

@description('BFF Container App Managed Identity Client ID')
output bffIdentityClientId string = bffIdentity.outputs.clientId

@description('Indexer Container Apps Job Managed Identity resource ID')
output indexerIdentityResourceId string = indexerIdentity.outputs.id

@description('Indexer Container Apps Job Managed Identity Client ID')
output indexerIdentityClientId string = indexerIdentity.outputs.clientId

@description('Log Analytics Workspace ID')
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId

@description('Application Insights Connection String')
@secure()
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString

@description('Application Insights Instrumentation Key')
@secure()
output appInsightsInstrumentationKey string = monitoring.outputs.appInsightsInstrumentationKey

@description('Key Vault URI')
output keyVaultUri string = keyVault.outputs.keyVaultUri

@description('Key Vault Name')
output keyVaultName string = keyVault.outputs.keyVaultName

@description('Container Registry Login Server')
output acrLoginServer string = containerRegistry.outputs.loginServer

@description('Container Registry Name')
output acrName string = containerRegistry.outputs.name

@description('Container Apps Environment Name')
output containerAppsEnvironmentName string = containerAppsEnvironment.outputs.name

@description('Container Apps Environment ID')
output containerAppsEnvironmentId string = containerAppsEnvironment.outputs.id

@description('Azure API Center Endpoint')
output apiCenterEndpoint string = apiCenter.outputs.endpoint

@description('Azure API Center Name')
output apiCenterName string = apiCenter.outputs.name

@description('Azure AI Search Endpoint')
output aiSearchEndpoint string = aiSearch.outputs.endpoint

@description('Azure AI Search Name')
output aiSearchName string = aiSearch.outputs.name

@description('Azure OpenAI Endpoint')
output openAiEndpoint string = openAi.outputs.endpoint

@description('Azure OpenAI Name')
output openAiName string = openAi.outputs.name

@description('Azure OpenAI Embedding Deployment Name')
output openAiEmbeddingDeploymentName string = openAi.outputs.embeddingDeploymentName

@description('Cosmos DB Endpoint')
output cosmosDbEndpoint string = cosmosDb.outputs.endpoint

@description('Cosmos DB Account Name')
output cosmosDbAccountName string = cosmosDb.outputs.accountName

@description('Cosmos DB Database Name')
output cosmosDbDatabaseName string = cosmosDb.outputs.databaseName

@description('Foundry Agent Service Account Name')
output foundryAccountName string = foundryAgent.outputs.accountName

@description('Foundry Agent Service Endpoint')
output foundryEndpoint string = foundryAgent.outputs.endpoint

@description('Foundry Project Name')
output foundryProjectName string = foundryAgent.outputs.projectName

@description('Foundry Chat Deployment Name')
output foundryChatDeploymentName string = foundryAgent.outputs.chatDeploymentName

@description('Azure Cache for Redis hostname')
output redisCacheHostName string = redisCache.outputs.hostName

@description('Azure Cache for Redis name')
output redisCacheName string = redisCache.outputs.name

// Note: Container App URLs will be available after deployment via bash script
@description('Frontend Container App Name (deploy separately)')
output frontendAppName string = resourceNames.frontendApp

@description('BFF Container App Name (deploy separately)')
output bffAppName string = resourceNames.bffApp

@description('Azure Load Testing resource name')
output loadTestName string = loadTesting.outputs.name

@description('Azure Load Testing data-plane endpoint')
output loadTestDataPlaneUri string = loadTesting.outputs.dataPlaneUri
