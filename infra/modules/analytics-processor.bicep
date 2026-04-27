// ============================================================================
// Analytics Processor Function App Module
// (Microsoft.App/containerApps, kind='functionapp')
// ============================================================================
// Deploys the analytics-processor as a NATIVE Functions-on-ACA container app
// — the v2 / recommended hosting model where the Functions runtime is
// provided by the Azure Container Apps platform.
//
// Replaces the legacy v1 proxy model
// (Microsoft.Web/sites kind='functionapp,linux,container,azurecontainerapps')
// which produced no first-class Container App resource, left the App Service
// Functions blade in a broken "Runtime version: Error" state, and offered
// no live logs / direct diagnostics.
//
// Refs:
//   https://learn.microsoft.com/azure/container-apps/functions-overview
//   https://learn.microsoft.com/azure/container-apps/migrate-functions
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

@description('CPU cores per replica')
param cpuCore string = '0.5'

@description('Memory per replica (e.g. 1Gi)')
param memorySize string = '1'

@description('Minimum replicas (0 enables scale-to-zero)')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 10

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

resource analyticsProcessor 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: containerAppName
  location: location
  tags: tags
  // kind='functionapp' opts this Container App into the native Azure Functions
  // hosting integration. The ACA platform injects the Functions host runtime;
  // our image only needs to ship the worker + function code (standard
  // mcr.microsoft.com/azure-functions/python base image).
  kind: 'functionapp'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironmentId
    workloadProfileName: workloadProfileName
    configuration: {
      activeRevisionsMode: 'Single'
      // No ingress: the analytics-processor is triggered exclusively by a
      // Service Bus queue. Adding ingress would cost an unnecessary public
      // FQDN and broaden the attack surface.
      // ACR pull via user-assigned managed identity (no admin user / no
      // password secrets).
      registries: [
        {
          server: acrLoginServer
          identity: managedIdentityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'analytics-processor'
          image: containerImage
          resources: {
            cpu: json(cpuCore)
            memory: '${memorySize}Gi'
          }
          // Functions host configuration. Identity-based connections use the
          // documented "__credential" / "__clientId" pattern. AZURE_CLIENT_ID
          // is intentionally NOT set — each connection prefix carries its own
          // identity client ID.
          env: [
            // -------- Functions runtime --------
            { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
            { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }

            // -------- Telemetry --------
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }

            // -------- AzureWebJobsStorage (identity-based) --------
            // __accountName shorthand lets the host derive blob/queue/table
            // endpoints internally with the constructor signature its
            // diagnostic event TableServiceClient factory expects.
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
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

// ----------------------------------------------------------------------------
// Diagnostic settings — required by project policy.
// Container console + system logs are captured by the managed environment's
// appLogsConfiguration (configured at the env level) and flow to the same
// Log Analytics workspace. Here we additionally enable platform metrics on
// the Container App resource for centralised observability and alerting.
// ----------------------------------------------------------------------------
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'send-to-log-analytics'
  scope: analyticsProcessor
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Analytics processor Container App resource ID')
output id string = analyticsProcessor.id

@description('Analytics processor Container App name')
output name string = analyticsProcessor.name

@description('Analytics processor Container App FQDN (empty when ingress is disabled)')
output defaultHostName string = ''
