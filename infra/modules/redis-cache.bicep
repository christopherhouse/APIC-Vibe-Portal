// ============================================================================
// Azure Cache for Redis Module
// ============================================================================
// Deploys an Azure Cache for Redis instance (Microsoft.Cache/redis) and
// grants the specified user-assigned managed identity data-plane access via
// an Entra ID access policy assignment (no access keys required).
//
// ⚠️  DEPRECATION NOTE (2026-04-16):
// Azure Cache for Redis is deprecated. This module replaces the previous
// Azure Managed Redis (Microsoft.Cache/redisEnterprise) module which could
// not be deployed (ARM failures both in CI and in the Azure Portal).
// This is an interim solution — revisit and migrate to the successor
// service once Azure Managed Redis deployment issues are resolved or a
// GA replacement is available.  See docs/project/apic_architecture.md for
// the full risk acknowledgment and remediation plan.
//
// Authentication: Entra ID / Managed Identity only.
// Access keys are disabled; the BFF acquires short-lived tokens from
// DefaultAzureCredential and authenticates without embedded secrets.
// ============================================================================

@description('Azure region')
param location string

@description('Azure Cache for Redis instance name')
param redisCacheName string

@description('Azure Cache for Redis SKU name (Basic, Standard, Premium)')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param redisSku string = 'Basic'

@description('Azure Cache for Redis SKU family (C = Basic/Standard, P = Premium)')
@allowed([
  'C'
  'P'
])
param redisFamily string = 'C'

@description('Azure Cache for Redis capacity (0-6 for C family, 1-5 for P family)')
param redisCapacity int = 0

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

// Azure Cache for Redis uses port 6380 for SSL connections
var redisPort = 6380

// ============================================================================
// RESOURCES
// ============================================================================

// Azure Cache for Redis
resource redisCache 'Microsoft.Cache/redis@2024-11-01' = {
  name: redisCacheName
  location: location
  tags: tags
  properties: {
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    disableAccessKeyAuthentication: true  // Entra ID only — no embedded secrets
    sku: {
      name: redisSku
      family: redisFamily
      capacity: redisCapacity
    }
    redisConfiguration: {
      'aad-enabled': 'true'
    }
  }
}

// Grant the user-assigned managed identity data-plane access to Redis.
// The built-in "Data Owner" access policy provides full read/write/admin
// access to all keys (required for SCAN + UNLINK cache clearing).
resource redisAccessPolicyAssignment 'Microsoft.Cache/redis/accessPolicyAssignments@2024-11-01' = {
  parent: redisCache
  name: take('bff-mi-${uniqueString(managedIdentityPrincipalId)}', 24)
  properties: {
    accessPolicyName: 'Data Owner'
    objectId: managedIdentityPrincipalId
    objectIdAlias: 'bff-managed-identity'
  }
}

// Diagnostic settings for Azure Cache for Redis
resource cacheDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
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

@description('Azure Cache for Redis resource ID')
output id string = redisCache.id

@description('Azure Cache for Redis name')
output name string = redisCache.name

@description('Azure Cache for Redis hostname (set as REDIS_HOST env var on the BFF at deploy time)')
output hostName string = redisCache.properties.hostName

@description('Azure Cache for Redis SSL port (6380)')
output port int = redisPort
