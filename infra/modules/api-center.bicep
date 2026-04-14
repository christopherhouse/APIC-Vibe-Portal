// ============================================================================
// Azure API Center Module
// ============================================================================

@description('Azure region')
param location string

@description('API Center name')
param apiCenterName string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

resource apiCenter 'Microsoft.ApiCenter/services@2024-03-01' = {
  name: apiCenterName
  location: location
  tags: tags
  properties: {}
}

// RBAC: Grant managed identity "Azure API Center Data Reader" role
resource apiCenterDataReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(apiCenter.id, managedIdentityPrincipalId, 'Azure API Center Data Reader')
  scope: apiCenter
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'c7244dfb-f447-457d-b2ba-3999044d1706') // Azure API Center Data Reader
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${apiCenterName}'
  scope: apiCenter
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'allLogs'
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

// ============================================================================
// OUTPUTS
// ============================================================================

@description('API Center resource ID')
output id string = apiCenter.id

@description('API Center name')
output name string = apiCenter.name

@description('API Center endpoint')
output endpoint string = 'https://${apiCenterName}.data.${location}.azure.microsoft.com'
