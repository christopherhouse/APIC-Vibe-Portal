// ============================================================================
// Container Apps Environment Module
// ============================================================================

@description('Azure region')
param location string

@description('Container Apps Environment name')
param containerAppsEnvName string

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Application Insights Connection String')
param appInsightsConnectionString string

@description('Resource tags')
param tags object

// ============================================================================
// RESOURCES
// ============================================================================

// Get Log Analytics workspace for shared key
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: split(logAnalyticsWorkspaceId, '/')[8]
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: appInsightsConnectionString
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Container Apps Environment resource ID')
output id string = containerAppsEnvironment.id

@description('Container Apps Environment name')
output name string = containerAppsEnvironment.name

@description('Container Apps Environment default domain')
output defaultDomain string = containerAppsEnvironment.properties.defaultDomain

@description('Container Apps Environment static IP')
output staticIp string = containerAppsEnvironment.properties.staticIp
