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

@description('Optional description for the load test resource')
@maxLength(512)
param loadTestDescription string = 'APIC Vibe Portal load testing resource'

// ============================================================================
// RESOURCES
// ============================================================================

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
