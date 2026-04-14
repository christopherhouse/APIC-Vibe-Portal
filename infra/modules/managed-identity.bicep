// ============================================================================
// Managed Identity Module - User-Assigned Managed Identity
// ============================================================================

@description('Azure region')
param location string

@description('Managed Identity name')
param managedIdentityName string

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: tags
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Managed Identity resource ID')
output id string = managedIdentity.id

@description('Managed Identity name')
output name string = managedIdentity.name

@description('Managed Identity Principal ID')
output principalId string = managedIdentity.properties.principalId

@description('Managed Identity Client ID')
output clientId string = managedIdentity.properties.clientId
