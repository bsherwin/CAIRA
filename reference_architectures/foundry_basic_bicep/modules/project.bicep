targetScope = 'resourceGroup'

@description('Location for all resources.')
param location string

@description('Tags to be applied to resources.')
param tags object = {}

@description('AI Foundry account name that hosts the project.')
param aiFoundryAccountName string

@description('Name of the AI Foundry project.')
param projectName string

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: aiFoundryAccountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  name: projectName
  parent: aiFoundry
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

@description('The resource ID of the AI Foundry project.')
output projectId string = project.id

@description('The name of the AI Foundry project.')
output projectName string = project.name

@description('The principal ID of the project managed identity.')
output projectPrincipalId string = project.identity.principalId
