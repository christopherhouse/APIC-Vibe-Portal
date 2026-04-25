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

resource analyticsProcessor 'Microsoft.App/containerApps@2024-03-01' = {
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
            { name: 'AzureWebJobsStorage__accountName', value: storageAccountName }
            { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
            { name: 'AzureWebJobsStorage__clientId', value: managedIdentityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'ServiceBusConnection__fullyQualifiedNamespace', value: serviceBusNamespace }
            { name: 'ServiceBusConnection__clientId', value: managedIdentityClientId }
            { name: 'CosmosDBConnection__accountEndpoint', value: cosmosDbEndpoint }
            { name: 'CosmosDBConnection__clientId', value: managedIdentityClientId }
            { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
            { name: 'ASPNETCORE_URLS', value: 'http://+:8080' }
            { name: 'AZURE_CLIENT_ID', value: managedIdentityClientId }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 10
        rules: [
          {
            name: 'service-bus-scale-rule'
            custom: {
              type: 'azure-servicebus'
              metadata: {
                topicName: 'analytics-events'
                subscriptionName: 'cosmos-writer'
                namespace: serviceBusNamespace
                messageCount: '50'
              }
              identity: managedIdentityResourceId
            }
          }
        ]
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
