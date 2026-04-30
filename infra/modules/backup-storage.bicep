// ============================================================================
// Backup Storage Module — Storage account + blob container for API Center backups
// ============================================================================
// Dedicated storage account that holds ZIP archives produced by the
// Container Apps Job defined in `src/backup-job/`.  Lifecycle management
// rules transition older backups to cooler tiers automatically.
// ============================================================================

@description('Azure region')
param location string

@description('Storage account name (3-24 lowercase alphanumeric chars)')
param storageAccountName string

@description('Backup blob container name')
param backupContainerName string = 'apic-backups'

@description('Backup job Managed Identity Principal ID — needs Storage Blob Data Contributor RBAC')
param backupIdentityPrincipalId string

@description('BFF Managed Identity Principal ID — needs Storage Blob Data Reader + User Delegation Key RBAC for SAS generation')
param bffIdentityPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Resource tags')
param tags object

// ============================================================================
// VARIABLES
// ============================================================================

// Built-in role IDs (https://learn.microsoft.com/azure/role-based-access-control/built-in-roles)
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageBlobDataReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
var storageBlobDelegatorRoleId = 'db58b8e5-c6ad-4a2a-8342-4190687cbf4a'

// ============================================================================
// RESOURCES
// ============================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    accessTier: 'Hot'
  }
}

// Blob service — enable soft delete + container soft delete for accidental loss protection
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 14
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 14
    }
    isVersioningEnabled: false
  }
}

// Backup blob container (private)
resource backupContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: backupContainerName
  properties: {
    publicAccess: 'None'
  }
}

// Lifecycle management — Hot → Cool after 30 days, Cool → Archive after 90 days
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'apic-backups-tiering'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: ['blockBlob']
              prefixMatch: ['${backupContainerName}/']
            }
            actions: {
              baseBlob: {
                tierToCool: { daysAfterModificationGreaterThan: 30 }
                tierToArchive: { daysAfterModificationGreaterThan: 90 }
              }
            }
          }
        }
      ]
    }
  }
}

// RBAC: backup job identity needs read/write on blobs
resource backupJobBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, backupIdentityPrincipalId, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: backupIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: BFF identity needs read on blobs (for download endpoint metadata)
resource bffBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, bffIdentityPrincipalId, 'StorageBlobDataReader')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataReaderRoleId)
    principalId: bffIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: BFF identity needs Storage Blob Delegator to mint user-delegation SAS tokens
resource bffBlobDelegator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, bffIdentityPrincipalId, 'StorageBlobDelegator')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDelegatorRoleId)
    principalId: bffIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${storageAccountName}'
  scope: storageAccount
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      {
        category: 'Transaction'
        enabled: true
        retentionPolicy: { enabled: false, days: 0 }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Storage account resource ID')
output id string = storageAccount.id

@description('Storage account name')
output name string = storageAccount.name

@description('Backup blob endpoint (e.g. https://acct.blob.core.windows.net)')
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('Backup container name')
output containerName string = backupContainerName
