// ============================================================================
// Azure Load Testing Module (Azure App Testing)
// ============================================================================
// Deploys an Azure Load Testing resource (Microsoft.LoadTestService/loadTests)
// which is part of the Azure App Testing platform.  Azure App Testing unifies
// Azure Load Testing (JMeter/Locust performance tests) and Microsoft Playwright
// Testing under a single management plane.
//
// The resource itself is lightweight — test plans, configs, and secrets are
// managed at the test-run level via the Azure Load Testing YAML config and
// the azure/load-testing GitHub Action.
//
// The system-assigned managed identity of the load test resource is granted
// "Key Vault Secrets User" on the shared Key Vault so that the ALT data-plane
// can resolve Key Vault secret URIs referenced in the test config YAML at
// run time (e.g. TOKEN_CLIENT_SECRET).  This avoids storing the client secret
// as a plain-text GitHub Actions secret.
//
// Diagnostics are sent to Log Analytics for observability.
// ============================================================================

@description('Azure region')
param location string

@description('Azure Load Testing resource name')
param loadTestName string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Resource tags')
param tags object

@description('Key Vault name — used to create the Key Vault Secrets User role assignment for ALT secret resolution')
param keyVaultName string

@description('Optional description for the load test resource')
@maxLength(512)
param loadTestDescription string = 'APIC Vibe Portal load testing resource'

// ============================================================================
// RESOURCES
// ============================================================================

// Reference the shared Key Vault to scope the role assignment
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource loadTest 'Microsoft.LoadTestService/loadTests@2022-12-01' = {
  name: loadTestName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    description: loadTestDescription
  }
}

// Grant the load test's system-assigned identity "Key Vault Secrets User"
// so the ALT data-plane can read Key Vault secret URIs in the test config.
resource keyVaultSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, loadTest.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User
    )
    principalId: loadTest.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings — send logs to Log Analytics
// Note: Microsoft.LoadTestService/loadTests does NOT support metric export;
// only the OperationLogs log category is available.
resource loadTestDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${loadTestName}'
  scope: loadTest
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'OperationLogs'
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

@description('Azure Load Testing resource ID')
output id string = loadTest.id

@description('Azure Load Testing resource name')
output name string = loadTest.name

@description('Azure Load Testing data-plane endpoint')
output dataPlaneUri string = loadTest.properties.dataPlaneURI

@description('Principal ID of the load test system-assigned managed identity')
output principalId string = loadTest.identity.principalId
