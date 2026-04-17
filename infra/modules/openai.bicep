// ============================================================================
// Azure OpenAI Module (Azure AI Services kind: AIServices)
// ============================================================================

@description('Azure region')
param location string

@description('Azure OpenAI/AI Services account name')
param openAiName string

@description('SKU name')
@allowed(['S0'])
param sku string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Indexer Container Job Managed Identity Principal ID for RBAC')
param indexerManagedIdentityPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Enable private endpoint')
param enablePrivateEndpoint bool

@description('Private endpoint subnet ID')
param privateEndpointSubnetId string

@description('Disable local (key-based) authentication in favour of RBAC (recommended)')
param disableLocalAuth bool = true

@description('Embedding model deployment name — must match OPENAI_EMBEDDING_DEPLOYMENT in indexer config')
param embeddingDeploymentName string = 'text-embedding-ada-002'

@description('Embedding model name (Azure OpenAI model identifier)')
param embeddingModelName string = 'text-embedding-ada-002'

@description('Embedding model version')
param embeddingModelVersion string = '2'

@description('Embedding deployment SKU name')
@allowed(['Standard', 'GlobalStandard', 'ProvisionedManaged'])
param embeddingDeploymentSkuName string = 'Standard'

@description('Embedding deployment capacity (in thousands of tokens per minute)')
param embeddingDeploymentCapacity int = 30

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

// Using Azure Verified Module pattern for AI Services (kind: AIServices)
resource cognitiveService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openAiName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateEndpoint ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
    disableLocalAuth: disableLocalAuth
  }
}

// Embedding model deployment (text-embedding-ada-002)
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: cognitiveService
  name: embeddingDeploymentName
  sku: {
    name: embeddingDeploymentSkuName
    capacity: embeddingDeploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
  }
}

// RBAC: Grant managed identity "Cognitive Services OpenAI User" role
resource openAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cognitiveService.id, managedIdentityPrincipalId, 'Cognitive Services OpenAI User')
  scope: cognitiveService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant indexer identity "Cognitive Services OpenAI User" — required for embedding generation
resource openAiUserRoleIndexer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cognitiveService.id, indexerManagedIdentityPrincipalId, 'Cognitive Services OpenAI User')
  scope: cognitiveService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
    principalId: indexerManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${openAiName}'
  scope: cognitiveService
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'Audit'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'RequestResponse'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
  }
}

// Private endpoint (if enabled)
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = if (enablePrivateEndpoint) {
  name: '${openAiName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${openAiName}-pe-connection'
        properties: {
          privateLinkServiceId: cognitiveService.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Cognitive Services account resource ID')
output id string = cognitiveService.id

@description('Cognitive Services account name')
output name string = cognitiveService.name

@description('Cognitive Services endpoint')
output endpoint string = cognitiveService.properties.endpoint

@description('Embedding model deployment name')
output embeddingDeploymentName string = embeddingDeployment.name
