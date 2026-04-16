// ============================================================================
// Azure Managed Redis Module
// ============================================================================
// Deploys an Azure Managed Redis instance (Microsoft.Cache/redisEnterprise)
// and grants the specified user-assigned managed identity data-plane access
// via an Entra ID access policy assignment (no access keys required).
//
// Authentication: Entra ID / Managed Identity only.
// Access keys are disabled; the BFF acquires short-lived tokens from
// DefaultAzureCredential and authenticates without embedded secrets.
// ============================================================================

@description('Azure region')
param location string

@description('Azure Managed Redis instance name')
param redisCacheName string

@description('Azure Managed Redis SKU name (e.g. Balanced_B0, Balanced_B1, MemoryOptimized_M10)')
param redisSku string = 'Balanced_B1'

@description('Principal ID of the user-assigned managed identity that will access Redis')
param managedIdentityPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Enable private endpoint')
param enablePrivateEndpoint bool

@description('Private endpoint subnet ID')
param privateEndpointSubnetId string

@description('Resource tags')
param tags object

// ============================================================================
// VARIABLES
// ============================================================================

// Azure Managed Redis Enterprise databases use port 10000 by default
var redisPort = 10000

// ============================================================================
// RESOURCES
// ============================================================================

// Azure Managed Redis cluster (Redis Enterprise)
resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2025-07-01' = {
  name: redisCacheName
  location: location
  tags: tags
  sku: {
    name: redisSku
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
  }
}

// Redis database within the cluster
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2025-07-01' = {
  parent: redisEnterprise
  name: 'default'
  properties: {
    accessKeysAuthentication: 'Disabled'  // Entra ID only — no embedded secrets
    evictionPolicy: 'VolatileLRU'         // Evict TTL-keyed entries, LRU order
    clusteringPolicy: 'EnterpriseCluster'
    port: redisPort
  }
}

// Grant the user-assigned managed identity data-plane access to the Redis database.
// The built-in "default" access policy provides read/write access to all keys.
resource redisAccessPolicyAssignment 'Microsoft.Cache/redisEnterprise/databases/accessPolicyAssignments@2025-07-01' = {
  parent: redisDatabase
  name: take('bff-mi-${uniqueString(managedIdentityPrincipalId)}', 24)
  properties: {
    accessPolicyName: 'default'
    user: {
      objectId: managedIdentityPrincipalId
    }
  }
}

// Diagnostic settings for the Redis Enterprise cluster
resource clusterDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${redisCacheName}'
  scope: redisEnterprise
  properties: {
    workspaceId: logAnalyticsWorkspaceId
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

// Private endpoint (if enabled — recommended for prod)
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = if (enablePrivateEndpoint) {
  name: '${redisCacheName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${redisCacheName}-pe-connection'
        properties: {
          privateLinkServiceId: redisEnterprise.id
          groupIds: [
            'redisEnterprise'
          ]
        }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Azure Managed Redis cluster resource ID')
output id string = redisEnterprise.id

@description('Azure Managed Redis cluster name')
output name string = redisEnterprise.name

@description('Azure Managed Redis hostname (set as REDIS_HOST env var on the BFF at deploy time)')
output hostName string = redisEnterprise.properties.hostName

@description('Azure Managed Redis database port (10000)')
output port int = redisPort
