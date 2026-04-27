// ============================================================================
// Analytics Processor Function App Module (Microsoft.Web/sites on ACA)
// ============================================================================
// Deploys the analytics-processor as a classic Function App
// (Microsoft.Web/sites kind=functionapp,linux,container,azurecontainerapps)
// hosted on the existing Azure Container Apps managed environment.
//
// We picked this hosting mode (over Microsoft.App/containerApps with
// kind=functionapp) because the App Service control plane is a battle-tested
// path for identity-based AzureWebJobsStorage / Service Bus / Cosmos DB
// connections; the kind=functionapp ACA path failed to initialise the
// Functions host's external startup classes in this project.
// ============================================================================

@description('Azure region')
param location string = resourceGroup().location

@description('Container App name')
param containerAppName string

@description('Container Apps Environment resource ID')
param containerAppsEnvironmentId string

@description('ACR login server (e.g. myacr.azurecr.io)')
param acrLoginServer string

@description('Container image tag (e.g. main or sha-abc123)')
param imageTag string

@description('Analytics processor UAMI resource ID (full ARM path)')
param managedIdentityResourceId string

@description('Analytics processor UAMI client ID')
param managedIdentityClientId string

@description('Function App storage account name (for AzureWebJobsStorage)')
param storageAccountName string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Service Bus fully qualified namespace (e.g. myns.servicebus.windows.net)')
param serviceBusNamespace string

@description('Cosmos DB account endpoint')
param cosmosDbEndpoint string

@description('Workload profile name on the ACA managed environment')
param workloadProfileName string = 'Consumption'

@description('Log Analytics Workspace resource ID for diagnostic settings')
param logAnalyticsWorkspaceId string

@description('Resource tags')
param tags object = {
  Application: 'APIC-Vibe-Portal'
  ManagedBy: 'Bicep'
  SecurityControl: 'Ignore'
}

// ============================================================================
// RESOURCES
// ============================================================================

// This module is deployed standalone from deploy-app.yml AFTER images are
// built and pushed to ACR — so the image always exists at deploy time.
var containerImage = '${acrLoginServer}/analytics-processor:${imageTag}'

resource analyticsProcessor 'Microsoft.Web/sites@2024-04-01' = {
  name: containerAppName
  location: location
  tags: tags
  kind: 'functionapp,linux,container,azurecontainerapps'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  }
  properties: {
    // Bind to the Container Apps managed environment (no serverFarmId).
    managedEnvironmentId: containerAppsEnvironmentId
    workloadProfileName: workloadProfileName
    httpsOnly: true
    clientAffinityEnabled: false
    // NOTE: `functionAppConfig` (runtime / scaleAndConcurrency / deployment) is
    // a Flex Consumption property and is silently ignored for the
    // `functionapp,linux,container,azurecontainerapps` kind — the RP returns
    // null on read regardless of what we send. ACA-hosted Function Apps are
    // configured purely through siteConfig.linuxFxVersion (the container image)
    // and the Container Apps environment. The Azure portal Functions blade
    // ("Runtime version: Error", empty Functions list) is a known cosmetic
    // limitation for this hosting kind — the App Service Functions blade does
    // not fully introspect ACA-hosted apps. Use the Container App resource
    // blade or Application Insights for management/observability.
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerImage}'
      // Pull the image from ACR using the user-assigned managed identity.
      // For Functions on ACA, this property requires the UAMI *resource ID*
      // (not its clientId) per the Azure validation error 51021.
      acrUseManagedIdentityCreds: true
      acrUserManagedIdentityID: managedIdentityResourceId
      // App settings = Function host configuration. Identity-based connections
      // are configured per-binding using the documented "__credential" /
      // "__clientId" pattern. AZURE_CLIENT_ID is intentionally NOT set —
      // each connection prefix carries its own identity client ID.
      appSettings: [
        // -------- Functions runtime --------
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }

        // -------- Container registry (required for linux,container) --------
        // For Functions on Azure Container Apps, the underlying ACA registry
        // validator requires a hostname-only value (no scheme), even though
        // classic App Service expected `https://...`. The ACA error
        // ContainerAppInvalidRegistryServerValue is the binding constraint.
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: acrLoginServer }

        // -------- Telemetry --------
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }

        // -------- AzureWebJobsStorage (identity-based) --------
        // Use the __accountName shorthand so the host derives blob/queue/table
        // endpoints internally with the constructor signature its diagnostic
        // event TableServiceClient factory expects. Setting the per-service
        // *ServiceUri keys causes "Unable to find matching constructor" errors
        // in the host's diagnostic logger.
        { name: 'AzureWebJobsStorage__accountName', value: storageAccountName }
        { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
        { name: 'AzureWebJobsStorage__clientId', value: managedIdentityClientId }

        // -------- Service Bus trigger (identity-based) --------
        { name: 'ServiceBusConnection__fullyQualifiedNamespace', value: serviceBusNamespace }
        { name: 'ServiceBusConnection__credential', value: 'managedidentity' }
        { name: 'ServiceBusConnection__clientId', value: managedIdentityClientId }

        // -------- Cosmos DB output binding (identity-based) --------
        { name: 'CosmosDBConnection__accountEndpoint', value: cosmosDbEndpoint }
        { name: 'CosmosDBConnection__credential', value: 'managedidentity' }
        { name: 'CosmosDBConnection__clientId', value: managedIdentityClientId }
      ]
    }
  }
}

// ----------------------------------------------------------------------------
// Diagnostic settings — required by project policy. Sends function host logs,
// platform logs, and metrics to Log Analytics for centralised observability.
// ----------------------------------------------------------------------------
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'send-to-log-analytics'
  scope: analyticsProcessor
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { category: 'FunctionAppLogs', enabled: true }
      { category: 'AppServiceConsoleLogs', enabled: true }
      { category: 'AppServicePlatformLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Analytics processor Function App resource ID')
output id string = analyticsProcessor.id

@description('Analytics processor Function App name')
output name string = analyticsProcessor.name

@description('Analytics processor Function App default hostname')
output defaultHostName string = analyticsProcessor.properties.defaultHostName
