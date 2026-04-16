// ============================================================================
// Azure Managed Redis Module
// ============================================================================
// Deploys an Azure Managed Redis instance (Microsoft.Cache/redisEnterprise)
// and stores the SSL connection string as a Key Vault secret so the BFF can
// retrieve it securely at runtime.
//
// Azure Managed Redis replaces the deprecated Azure Cache for Redis tiers and
// uses the Enterprise-grade Redis cluster architecture with a database
// sub-resource on port 10000.
// ============================================================================

@description('Azure region')
param location string

@description('Azure Managed Redis instance name')
param redisCacheName string

@description('Azure Managed Redis SKU name (e.g. Balanced_B0, Balanced_B1, MemoryOptimized_M10)')
param redisSku string = 'Balanced_B1'

@description('Key Vault name where the Redis connection string secret will be stored')
param keyVaultName string

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
resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2024-09-01-preview' = {
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
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2024-09-01-preview' = {
  parent: redisEnterprise
  name: 'default'
  properties: {
    accessKeysAuthentication: 'Enabled'   // Access key stored in Key Vault
    evictionPolicy: 'VolatileLRU'         // Evict TTL-keyed entries, LRU order
    clusteringPolicy: 'EnterpriseCluster'
    port: redisPort
  }
}

// Store the SSL connection URL as a Key Vault secret so the BFF reads it
// without the key ever appearing in environment variables or source code.
resource keyVaultRef 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Build the redis-py SSL URL from its components for readability.
var redisHostName = redisEnterprise.properties.hostName
var redisPrimaryKey = listKeys(redisDatabase.id, redisDatabase.apiVersion).primaryKey
var redisConnectionString = 'rediss://:${redisPrimaryKey}@${redisHostName}:${redisPort}'

resource redisConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVaultRef
  name: 'redis-connection-string'
  properties: {
    value: redisConnectionString
    contentType: 'text/plain'
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

@description('Azure Managed Redis hostname')
output hostName string = redisEnterprise.properties.hostName

@description('Azure Managed Redis database port (10000)')
output port int = redisPort

@description('Key Vault secret name holding the Redis connection string')
output connectionStringSecretName string = redisConnectionStringSecret.name
