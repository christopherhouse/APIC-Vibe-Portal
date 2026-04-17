// ============================================================================
// Azure API Center Module
// ============================================================================

@description('Azure region')
param location string

@description('API Center name')
param apiCenterName string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Indexer Container Job Managed Identity Principal ID for RBAC')
param indexerManagedIdentityPrincipalId string

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

resource apiCenter 'Microsoft.ApiCenter/services@2024-03-01' = {
  name: apiCenterName
  location: location
  tags: tags
  sku: {
    name: 'Free'
  }
  properties: {}
}

// RBAC: Grant managed identity "Azure API Center Data Reader" role (data-plane reads)
resource apiCenterDataReaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(apiCenter.id, managedIdentityPrincipalId, 'Azure API Center Data Reader')
  scope: apiCenter
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'c7244dfb-f447-457d-b2ba-3999044d1706') // Azure API Center Data Reader
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Custom Role: API Center Catalog Contributor
// Grants read/write on catalog items (APIs, versions, definitions, deployments)
// without service-level permissions (cannot modify the service itself, metadata
// schemas, workspaces, or deleted-service operations).
resource apiCenterCatalogContributorDef 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscription().id, resourceGroup().id, 'API Center Catalog Contributor')
  properties: {
    roleName: 'API Center Catalog Contributor (${resourceGroup().name})'
    description: 'Read and write API catalog items (APIs, versions, definitions, deployments) in Azure API Center. Does not grant service-level management permissions.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          // Read service & workspace metadata (required to navigate the resource hierarchy)
          'Microsoft.ApiCenter/services/read'
          'Microsoft.ApiCenter/services/workspaces/read'
          // APIs — full CRUD
          'Microsoft.ApiCenter/services/workspaces/apis/read'
          'Microsoft.ApiCenter/services/workspaces/apis/write'
          'Microsoft.ApiCenter/services/workspaces/apis/delete'
          // Versions — full CRUD
          'Microsoft.ApiCenter/services/workspaces/apis/versions/read'
          'Microsoft.ApiCenter/services/workspaces/apis/versions/write'
          'Microsoft.ApiCenter/services/workspaces/apis/versions/delete'
          // Definitions — full CRUD + import/export
          'Microsoft.ApiCenter/services/workspaces/apis/versions/definitions/read'
          'Microsoft.ApiCenter/services/workspaces/apis/versions/definitions/write'
          'Microsoft.ApiCenter/services/workspaces/apis/versions/definitions/delete'
          'Microsoft.ApiCenter/services/workspaces/apis/versions/definitions/exportSpecification/action'
          'Microsoft.ApiCenter/services/workspaces/apis/versions/definitions/importSpecification/action'
          // Deployments — full CRUD
          'Microsoft.ApiCenter/services/workspaces/apis/deployments/read'
          'Microsoft.ApiCenter/services/workspaces/apis/deployments/write'
          'Microsoft.ApiCenter/services/workspaces/apis/deployments/delete'
          // Environments — read only (needed to reference environments in deployments)
          'Microsoft.ApiCenter/services/workspaces/environments/read'
        ]
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
    assignableScopes: [
      resourceGroup().id
    ]
  }
}

// RBAC: Assign the custom Catalog Contributor role to the BFF managed identity
resource apiCenterCatalogContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(apiCenter.id, managedIdentityPrincipalId, 'API Center Catalog Contributor')
  scope: apiCenter
  properties: {
    roleDefinitionId: apiCenterCatalogContributorDef.id
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant indexer identity "Azure API Center Service Reader" — required to enumerate
// APIs via the management plane SDK (azure-mgmt-apicenter).
// Note: The previous role "Azure API Center Data Reader" (c7244dfb-...) only grants
// DataActions (data plane).  The management plane SDK needs control-plane Actions
// (Microsoft.ApiCenter/services/*/read) which are included in Service Reader.
resource apiCenterServiceReaderRoleIndexer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(apiCenter.id, indexerManagedIdentityPrincipalId, 'Azure API Center Service Reader')
  scope: apiCenter
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '6cba8790-29c5-48e5-bab1-c7541b01cb04') // Azure API Center Service Reader
    principalId: indexerManagedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Note: Azure API Center does not support diagnostic settings as of API version 2024-03-01

// ============================================================================
// OUTPUTS
// ============================================================================

@description('API Center resource ID')
output id string = apiCenter.id

@description('API Center name')
output name string = apiCenter.name

@description('API Center endpoint')
output endpoint string = 'https://${apiCenterName}.data.${location}.azure.microsoft.com'
