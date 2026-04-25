// ============================================================================
// Analytics Processor Container App Module (kind: functionapp)
// ============================================================================
// Deploys the analytics-processor as a native Function App on Container Apps
// using Microsoft.App/containerApps with kind=functionapp.
// The Function is triggered by Service Bus messages and writes to Cosmos DB.
// No HTTP ingress is needed — pure event consumer.
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
  kind: 'functionapp'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      // Internal ingress is required even for non-HTTP triggered functions.
      // The Container Apps platform communicates with the Functions host
      // for function discovery, health probes, and lifecycle management.
      ingress: {
        external: false
        targetPort: 8080
        transport: 'auto'
      }
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
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            // Identity-based connection to AzureWebJobsStorage. We use the
            // explicit *ServiceUri form (not __accountName) because the
            // shorthand has compatibility issues on Container Apps with
            // kind=functionapp — see
            // https://learn.microsoft.com/azure/azure-functions/functions-reference#connecting-to-host-storage-with-an-identity
            { name: 'AzureWebJobsStorage__blobServiceUri', value: 'https://${storageAccountName}.blob.${environment().suffixes.storage}' }
            { name: 'AzureWebJobsStorage__queueServiceUri', value: 'https://${storageAccountName}.queue.${environment().suffixes.storage}' }
            { name: 'AzureWebJobsStorage__tableServiceUri', value: 'https://${storageAccountName}.table.${environment().suffixes.storage}' }
            { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
            { name: 'AzureWebJobsStorage__clientId', value: managedIdentityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'ServiceBusConnection__fullyQualifiedNamespace', value: serviceBusNamespace }
            { name: 'ServiceBusConnection__credential', value: 'managedidentity' }
            { name: 'ServiceBusConnection__clientId', value: managedIdentityClientId }
            { name: 'CosmosDBConnection__accountEndpoint', value: cosmosDbEndpoint }
            { name: 'CosmosDBConnection__credential', value: 'managedidentity' }
            { name: 'CosmosDBConnection__clientId', value: managedIdentityClientId }
            { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
            { name: 'ASPNETCORE_URLS', value: 'http://+:8080' }
            // NOTE: do NOT set AZURE_CLIENT_ID here. Per Microsoft docs:
            // "Use of the Azure SDK's EnvironmentCredential environment
            // variables is not recommended due to the potentially unintentional
            // impact on other connections. They also are not fully supported
            // when deployed to Azure Functions."
            // Each connection (AzureWebJobsStorage, ServiceBusConnection,
            // CosmosDBConnection) gets its identity from its own __clientId.
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 10
      }
    }
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Analytics processor Container App resource ID')
output id string = analyticsProcessor.id

@description('Analytics processor Container App name')
output name string = analyticsProcessor.name
