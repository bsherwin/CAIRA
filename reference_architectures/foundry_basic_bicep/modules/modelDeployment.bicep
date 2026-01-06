targetScope = 'resourceGroup'

@description('AI Foundry account name that hosts the deployment.')
param aiFoundryAccountName string

@description('Deployment name.')
param deploymentName string

@description('Model format (e.g., OpenAI).')
param modelFormat string

@description('Model name (e.g., gpt-4.1).')
param modelName string

@description('Model version (e.g., 2025-04-14).')
param modelVersion string

@description('Deployment SKU name (e.g., GlobalStandard).')
param skuName string

@description('Deployment SKU capacity.')
param skuCapacity int

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: aiFoundryAccountName
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  name: deploymentName
  parent: aiFoundry
  sku: {
    name: skuName
    capacity: skuCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
  }
}

@description('The resource ID of the model deployment.')
output deploymentId string = deployment.id
