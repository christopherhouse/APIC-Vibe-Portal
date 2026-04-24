// ============================================================================
// Azure Service Bus Module (Standard SKU, Entra-only auth)
// ============================================================================

@description('Azure region')
param location string

@description('Service Bus namespace name')
param serviceBusNamespaceName string

@description('BFF Managed Identity Principal ID — granted Data Sender role')
param senderPrincipalId string

@description('Analytics processor Managed Identity Principal ID — granted Data Receiver role')
param receiverPrincipalId string

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Enable private endpoint')
param enablePrivateEndpoint bool

@description('Private endpoint subnet ID')
param privateEndpointSubnetId string

@description('Resource tags')
param tags object

// ============================================================================
// VARIABLES
// ============================================================================

var topicName = 'analytics-events'
var subscriptionName = 'cosmos-writer'

// Azure built-in role IDs
var serviceBusDataSenderRoleId = '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39'
var serviceBusDataReceiverRoleId = '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0'

// ============================================================================
// RESOURCES
// ============================================================================

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: serviceBusNamespaceName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    disableLocalAuth: true
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    minimumTlsVersion: '1.2'
  }
}

resource topic 'Microsoft.ServiceBus/namespaces/topics@2024-01-01' = {
  parent: serviceBusNamespace
  name: topicName
  properties: {
    maxSizeInMegabytes: 1024
    defaultMessageTimeToLive: 'P14D' // 14 days
  }
}

resource subscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2024-01-01' = {
  parent: topic
  name: subscriptionName
  properties: {
    maxDeliveryCount: 10
    lockDuration: 'PT5M'
    deadLetteringOnMessageExpiration: true
    defaultMessageTimeToLive: 'P14D'
  }
}

// Default "all messages" filter rule (1=1)
resource filterRule 'Microsoft.ServiceBus/namespaces/topics/subscriptions/rules@2024-01-01' = {
  parent: subscription
  name: 'all-messages'
  properties: {
    filterType: 'SqlFilter'
    sqlFilter: {
      sqlExpression: '1=1'
    }
  }
}

// RBAC: Grant BFF identity "Azure Service Bus Data Sender" role
resource senderRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(serviceBusNamespace.id, senderPrincipalId, 'ServiceBusDataSender')
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', serviceBusDataSenderRoleId)
    principalId: senderPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// RBAC: Grant analytics processor identity "Azure Service Bus Data Receiver" role
resource receiverRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(serviceBusNamespace.id, receiverPrincipalId, 'ServiceBusDataReceiver')
  scope: serviceBusNamespace
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', serviceBusDataReceiverRoleId)
    principalId: receiverPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings
resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-${serviceBusNamespaceName}'
  scope: serviceBusNamespace
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'OperationalLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'VNetAndIPFilteringLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'RuntimeAuditLogs'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
  }
}

// Private endpoint (if enabled)
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = if (enablePrivateEndpoint) {
  name: '${serviceBusNamespaceName}-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${serviceBusNamespaceName}-pe-connection'
        properties: {
          privateLinkServiceId: serviceBusNamespace.id
          groupIds: [
            'namespace'
          ]
        }
      }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Service Bus namespace resource ID')
output id string = serviceBusNamespace.id

@description('Service Bus namespace name')
output namespaceName string = serviceBusNamespace.name

@description('Service Bus fully qualified namespace (e.g. myns.servicebus.windows.net)')
output fullyQualifiedNamespace string = '${serviceBusNamespace.name}.servicebus.windows.net'

@description('Service Bus topic name')
output topicName string = topicName

@description('Service Bus subscription name')
output subscriptionName string = subscriptionName
