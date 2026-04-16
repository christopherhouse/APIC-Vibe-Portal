// ============================================================================
// Dev Environment Parameters
// No VNet, no private endpoints — public access for simplicity.
// ============================================================================

using '../main.bicep'

param environmentName = 'dev'
param namePrefix = 'apicvibe'
param aiSearchSku = 'basic'
param keyVaultSku = 'standard'
param enablePrivateEndpoints = false
param privateEndpointSubnetId = ''
param cosmosDbLocation = 'eastus2'
param redisSku = 'Balanced_B0'
