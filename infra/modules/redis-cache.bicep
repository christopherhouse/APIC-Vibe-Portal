// ============================================================================
// Azure Cache for Redis Module
// ============================================================================
// Deploys an Azure Cache for Redis instance and stores the SSL connection
// string as a Key Vault secret so the BFF can retrieve it securely at runtime.
// ============================================================================

@description('Azure region')
param location string

@description('Redis cache name')
param redisCacheName string

@description('Redis cache SKU (Basic, Standard, Premium)')
@allowed(['Basic', 'Standard', 'Premium'])
param redisSku string = 'Standard'

@description('Redis cache SKU capacity (0–6 for Basic/Standard, 1–4 for Premium)')
param redisSkuCapacity int = 1

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

var redisSkuFamily = redisSku == 'Premium' ? 'P' : 'C'

// ============================================================================
// RESOURCES
// ============================================================================

resource redisCache 'Microsoft.Cache/redis@2024-03-01' = {
  name: redisCacheName
  location: location
  tags: tags
  properties: {
    sku: {
      name: redisSku
      family: redisSkuFamily
      capacity: redisSkuCapacity
    }
    enableNonSslPort: false       // SSL only — port 6380
    minimumTlsVersion: '1.2'
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    redisConfiguration: {
      // Enable keyspace notifications for cache-miss observability (optional)
      'notify-keyspace-events': ''
    }
  }
}

// Store the SSL connection URL as a Key Vault secret so the BFF reads it
// without the key ever appearing in environment variables or source code.
resource keyVaultRef 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Build the redis-py SSL URL from its components for readability.
var redisHostName = redisCache.properties.hostName
var redisSslPort = redisCache.properties.sslPort
var redisPrimaryKey = listKeys(redisCache.id, redisCache.apiVersion).primaryKey
var redisConnectionString = 'rediss://:${redisPrimaryKey}@${redisHostName}:${redisSslPort}'

resource redisConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVaultRef
  name: 'redis-connection-string'
  properties: {
    value: redisConnectionString
    contentType: 'text/plain'
  }
}

// Diagnostic settings — AllMetrics (Basic/Standard tiers do not expose log categories)
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${redisCacheName}'
  scope: redisCache
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
          privateLinkServiceId: redisCache.id
          groupIds: [
            'redisCache'
          ]
        }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Redis cache resource ID')
output id string = redisCache.id

@description('Redis cache name')
output name string = redisCache.name

@description('Redis cache hostname')
output hostName string = redisCache.properties.hostName

@description('Redis SSL port (6380)')
output sslPort int = redisCache.properties.sslPort

@description('Key Vault secret name holding the Redis connection string')
output connectionStringSecretName string = redisConnectionStringSecret.name
