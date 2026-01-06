targetScope = 'resourceGroup'

@description('Location for all resources.')
param location string

@description('Tags to be applied to resources.')
param tags object = {}

@description('Name of the AI Foundry account.')
param aiFoundryAccountName string

@description('The SKU for the AI Foundry resource. The default is \'S0\'.')
param sku string = 'S0'

@description('Application Insights connection name to attach to the Foundry account.')
param applicationInsightsName string

@description('Application Insights resource ID to attach to the Foundry account.')
param applicationInsightsResourceId string

@secure()
@description('Application Insights connection string used as the credential key.')
param applicationInsightsConnectionString string

@description('Optional subnet resource ID for agents. If not provided, a capability host is created (Terraform parity).')
param agentsSubnetResourceId string = ''

@description('Set to true to restore the AI Foundry account if the name is currently soft-deleted in this subscription/location.')
param restoreAiFoundryAccount bool = false

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiFoundryAccountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    restore: restoreAiFoundryAccount
    disableLocalAuth: true
    allowProjectManagement: true
    customSubDomainName: aiFoundryAccountName
    publicNetworkAccess: 'Enabled'
  }
}


resource capabilityHost 'Microsoft.CognitiveServices/accounts/capabilityHosts@2025-04-01-preview' = if (empty(agentsSubnetResourceId)) {
  name: '${aiFoundry.name}-agents-capability-host'
  parent: aiFoundry
  properties: {
    capabilityHostKind: 'Agents'
  }
}

module deployGpt41 './modelDeployment.bicep' = {
  name: 'deployGpt41'
  dependsOn: empty(agentsSubnetResourceId) ? [capabilityHost] : []
  params: {
    aiFoundryAccountName: aiFoundry.name
    deploymentName: 'gpt-4.1'
    modelFormat: 'OpenAI'
    modelName: 'gpt-4.1'
    modelVersion: '2025-04-14'
    skuName: 'GlobalStandard'
    skuCapacity: 1
  }
}

module deployO4Mini './modelDeployment.bicep' = {
  name: 'deployO4Mini'
  dependsOn: [
    deployGpt41
  ]
  params: {
    aiFoundryAccountName: aiFoundry.name
    deploymentName: 'o4-mini'
    modelFormat: 'OpenAI'
    modelName: 'o4-mini'
    modelVersion: '2025-04-16'
    skuName: 'GlobalStandard'
    skuCapacity: 1
  }
}

module deployTextEmbedding3Large './modelDeployment.bicep' = {
  name: 'deployTextEmbedding3Large'
  dependsOn: [
    deployO4Mini
  ]
  params: {
    aiFoundryAccountName: aiFoundry.name
    deploymentName: 'text-embedding-3-large'
    modelFormat: 'OpenAI'
    modelName: 'text-embedding-3-large'
    modelVersion: '1'
    skuName: 'GlobalStandard'
    skuCapacity: 1
  }
}

resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/connections@2025-06-01' = {
  name: applicationInsightsName
  parent: aiFoundry
  dependsOn: [
    deployTextEmbedding3Large
  ]
  properties: {
    category: 'AppInsights'
    target: applicationInsightsResourceId
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: applicationInsightsConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: applicationInsightsResourceId
    }
  }
}

@description('The resource ID of the AI Foundry account.')
output aiFoundryId string = aiFoundry.id

@description('The name of the AI Foundry account.')
output aiFoundryName string = aiFoundry.name

@description('The endpoint URL of the AI Foundry account.')
output aiFoundryEndpoint string = aiFoundry.properties.endpoint

@description('The IDs of the AI Foundry model deployments.')
output aiFoundryModelDeploymentIds array = [
  deployGpt41.outputs.deploymentId
  deployO4Mini.outputs.deploymentId
  deployTextEmbedding3Large.outputs.deploymentId
]
