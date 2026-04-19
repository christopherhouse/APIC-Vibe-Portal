// ============================================================================
// Azure AI Foundry Agent Service Module
// ============================================================================
// Provisions Azure AI Foundry (Cognitive Services kind: AIServices) account
// and project for multi-agent orchestration.
//
// Based on working example from:
// https://github.com/microsoft-foundry/foundry-samples/blob/main/infrastructure/infrastructure-setup-bicep/00-basic/main.bicep
//
// Resources:
// - Microsoft.CognitiveServices/accounts (kind: AIServices)
// - Microsoft.CognitiveServices/accounts/projects
// ============================================================================

@description('Azure region')
param location string

@description('Foundry account name (AI Services account)')
param foundryAccountName string

@description('Foundry project name')
param foundryProjectName string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Enable private endpoint')
param enablePrivateEndpoint bool

@description('Private endpoint subnet ID')
param privateEndpointSubnetId string

@description('Disable local (key-based) authentication in favour of RBAC (recommended)')
param disableLocalAuth bool = true

@description('Chat model deployment name')
param chatDeploymentName string = 'gpt-4o'

@description('Chat model name (Azure OpenAI model identifier)')
param chatModelName string = 'gpt-4o'

@description('Chat model version')
param chatModelVersion string = '2024-11-20'

@description('Chat deployment SKU name')
@allowed(['Standard', 'GlobalStandard', 'ProvisionedManaged'])
param chatDeploymentSkuName string = 'GlobalStandard'

@description('Chat deployment capacity (in thousands of tokens per minute)')
param chatDeploymentCapacity int = 80

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

// Foundry Account (AI Services account with kind: AIServices)
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryAccountName
  location: location
  tags: tags
  kind: 'AIServices' // Required for Foundry
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: foundryAccountName
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateEndpoint ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
    disableLocalAuth: disableLocalAuth
    allowProjectManagement: true // Required to create projects under this account
    apiProperties: {}
  }
}

// Chat model deployment (gpt-4o)
resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundryAccount
  name: chatDeploymentName
  sku: {
    name: chatDeploymentSkuName
    capacity: chatDeploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: chatModelVersion
    }
  }
}

// Foundry Project (attached to account)
resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundryAccount
  name: foundryProjectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
  dependsOn: [
    chatDeployment
  ]
}

// RBAC: Grant managed identity "Cognitive Services OpenAI User" role
resource foundryUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccount.id, managedIdentityPrincipalId, 'Cognitive Services OpenAI User')
  scope: foundryAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant managed identity "Cognitive Services User" role for broader access
resource foundryContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccount.id, managedIdentityPrincipalId, 'Cognitive Services User')
  scope: foundryAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings for Foundry account
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${foundryAccountName}'
  scope: foundryAccount
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
  name: '${foundryAccountName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${foundryAccountName}-pe-connection'
        properties: {
          privateLinkServiceId: foundryAccount.id
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

@description('Foundry account resource ID')
output id string = foundryAccount.id

@description('Foundry account name')
output accountName string = foundryAccount.name

@description('Foundry endpoint')
output endpoint string = foundryAccount.properties.endpoint

@description('Foundry project resource ID')
output projectId string = foundryProject.id

@description('Foundry project name')
output projectName string = foundryProject.name

@description('Chat model deployment name')
output chatDeploymentName string = chatDeployment.name
