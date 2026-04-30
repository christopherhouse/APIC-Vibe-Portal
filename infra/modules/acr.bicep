// ============================================================================
// Azure Container Registry Module
// ============================================================================

@description('Azure region')
param location string

@description('ACR name')
param acrName string

@description('Frontend Managed Identity Principal ID for AcrPull RBAC')
param frontendManagedIdentityPrincipalId string

@description('BFF Managed Identity Principal ID for AcrPull RBAC')
param bffManagedIdentityPrincipalId string

@description('Indexer Container Job Managed Identity Principal ID for AcrPull RBAC')
param indexerManagedIdentityPrincipalId string

@description('Governance Snapshot Container Job Managed Identity Principal ID for AcrPull RBAC')
param governanceManagedIdentityPrincipalId string

@description('Analytics Processor Managed Identity Principal ID for AcrPull RBAC')
param analyticsProcessorManagedIdentityPrincipalId string

@description('Backup Container Job Managed Identity Principal ID for AcrPull RBAC')
param backupManagedIdentityPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Enable private endpoint')
param enablePrivateEndpoint bool

@description('Private endpoint subnet ID')
param privateEndpointSubnetId string

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false // Use managed identity instead
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
  }
}

// RBAC: Grant frontend managed identity "AcrPull" role
resource acrPullRoleFrontend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, frontendManagedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: frontendManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant BFF managed identity "AcrPull" role
resource acrPullRoleBff 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, bffManagedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: bffManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant indexer managed identity "AcrPull" role
resource acrPullRoleIndexer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, indexerManagedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: indexerManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant governance snapshot job managed identity "AcrPull" role
resource acrPullRoleGovernance 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, governanceManagedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: governanceManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant analytics processor managed identity "AcrPull" role
resource acrPullRoleAnalyticsProcessor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, analyticsProcessorManagedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: analyticsProcessorManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant backup job managed identity "AcrPull" role
resource acrPullRoleBackup 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, backupManagedIdentityPrincipalId, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: backupManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${acrName}'
  scope: containerRegistry
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'ContainerRegistryRepositoryEvents'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'ContainerRegistryLoginEvents'
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
  name: '${acrName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${acrName}-pe-connection'
        properties: {
          privateLinkServiceId: containerRegistry.id
          groupIds: [
            'registry'
          ]
        }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Container Registry resource ID')
output id string = containerRegistry.id

@description('Container Registry name')
output name string = containerRegistry.name

@description('Container Registry login server')
output loginServer string = containerRegistry.properties.loginServer
