// ============================================================================
// Azure Cosmos DB Module (Serverless, NoSQL API)
// ============================================================================

@description('Azure region')
param location string

@description('Cosmos DB Account name')
param cosmosDbAccountName string

@description('Managed Identity Principal ID for RBAC')
param managedIdentityPrincipalId string

@description('Additional failover locations (empty for single-region serverless)')
param additionalLocations array

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Enable private endpoint')
param enablePrivateEndpoint bool

@description('Private endpoint subnet ID')
param privateEndpointSubnetId string

@description('Disable local (key-based) authentication in favour of RBAC (recommended)')
param disableLocalAuth bool = true

@description('Resource tags')
param tags object

// ============================================================================
// VARIABLES
// ============================================================================

var databaseName = 'apic-vibe-portal'

// Build additional locations array
var additionalLocationsArray = [for (loc, i) in additionalLocations: {
  locationName: loc
  failoverPriority: i + 1
  isZoneRedundant: false
}]

// Build full locations array (primary + additional)
var locations = concat([
  {
    locationName: location
    failoverPriority: 0
    isZoneRedundant: false
  }
], additionalLocationsArray)

// ============================================================================
// RESOURCES
// ============================================================================

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' = {
  name: cosmosDbAccountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: locations
    enableAutomaticFailover: length(additionalLocations) > 0
    enableMultipleWriteLocations: false
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    networkAclBypass: 'AzureServices'
    disableLocalAuth: disableLocalAuth
    capabilities: [
      {
        name: 'EnableServerless' // Serverless capacity mode
      }
    ]
  }
}

// Create database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' = {
  parent: cosmosDbAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// RBAC: Grant managed identity "Cosmos DB Built-in Data Contributor" role
resource cosmosDbDataContributorRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-12-01-preview' = {
  name: guid(cosmosDbAccount.id, managedIdentityPrincipalId, 'Cosmos DB Built-in Data Contributor')
  parent: cosmosDbAccount
  properties: {
    roleDefinitionId: '${cosmosDbAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002' // Built-in Data Contributor
    principalId: managedIdentityPrincipalId
    scope: cosmosDbAccount.id
  }
}

// Diagnostic settings
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${cosmosDbAccountName}'
  scope: cosmosDbAccount
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'DataPlaneRequests'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'QueryRuntimeStatistics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'PartitionKeyStatistics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'ControlPlaneRequests'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
    metrics: [
      {
        category: 'Requests'
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
  name: '${cosmosDbAccountName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${cosmosDbAccountName}-pe-connection'
        properties: {
          privateLinkServiceId: cosmosDbAccount.id
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Cosmos DB Account resource ID')
output id string = cosmosDbAccount.id

@description('Cosmos DB Account name')
output accountName string = cosmosDbAccount.name

@description('Cosmos DB endpoint')
output endpoint string = cosmosDbAccount.properties.documentEndpoint

@description('Cosmos DB database name')
output databaseName string = databaseName

@description('Cosmos DB database resource ID')
output databaseId string = database.id
