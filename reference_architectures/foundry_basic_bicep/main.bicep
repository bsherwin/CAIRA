targetScope = 'subscription'

@description('Azure region where the resources should be deployed.')
param location string = 'swedencentral'

@description('The resource group name where the module resources will be deployed. If not provided, a new resource group will be created.')
param resourceGroupName string = ''

@description('The SKU for the AI Foundry resource. The default is \'S0\'.')
param sku string = 'S0'

@description('Set to true to restore the AI Foundry account if the name is currently soft-deleted in this subscription/location.')
param restoreAiFoundryAccount bool = false

@description('This variable controls whether or not telemetry is enabled for the modules. For more information see https://aka.ms/avm/telemetryinfo. If it is set to false, then no telemetry will be collected.')
#disable-next-line no-unused-params
param enableTelemetry bool = true

@description('(Optional) Tags to be applied to all resources.')
param tags object = {}

var baseName = 'basic'
var uniqueSuffix = toLower(take(uniqueString(subscription().id, baseName, location), 5))

var createResourceGroup = empty(resourceGroupName)
var computedResourceGroupName = 'rg-${baseName}-${uniqueSuffix}'
var targetResourceGroupName = createResourceGroup ? computedResourceGroupName : resourceGroupName

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = if (createResourceGroup) {
  name: targetResourceGroupName
  location: location
  tags: tags
}

var logAnalyticsWorkspaceName = 'log-${baseName}-${uniqueSuffix}'
var applicationInsightsName = 'appi-${baseName}-${uniqueSuffix}'
var aiFoundryAccountName = 'aif-${baseName}-${uniqueSuffix}'
var aiFoundryProjectName = 'proj-${baseName}-${uniqueSuffix}'

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: resourceGroup(targetResourceGroupName)
  dependsOn: [
    rg
  ]
  params: {
    location: location
    tags: tags
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
  }
}

module aiFoundry './modules/aiFoundry.bicep' = {
  name: 'aiFoundry'
  scope: resourceGroup(targetResourceGroupName)
  dependsOn: [
    rg
  ]
  params: {
    location: location
    tags: tags
    aiFoundryAccountName: aiFoundryAccountName
    sku: sku
    restoreAiFoundryAccount: restoreAiFoundryAccount
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    applicationInsightsResourceId: monitoring.outputs.applicationInsightsId
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
  }
}

module defaultProject './modules/project.bicep' = {
  name: 'defaultProject'
  scope: resourceGroup(targetResourceGroupName)
  dependsOn: [
    rg
  ]
  params: {
    location: location
    tags: tags
    aiFoundryAccountName: aiFoundry.outputs.aiFoundryName
    projectName: aiFoundryProjectName
  }
}

@description('The resource ID of the AI Foundry account.')
output ai_foundry_id string = aiFoundry.outputs.aiFoundryId

@description('The name of the AI Foundry account.')
output ai_foundry_name string = aiFoundry.outputs.aiFoundryName

@description('The endpoint URL of the AI Foundry account.')
output ai_foundry_endpoint string = aiFoundry.outputs.aiFoundryEndpoint

@description('The IDs of the AI Foundry model deployments.')
output ai_foundry_model_deployments_ids array = aiFoundry.outputs.aiFoundryModelDeploymentIds

@description('The resource ID of the resource group.')
output resource_group_id string = createResourceGroup ? rg.id : resourceId('Microsoft.Resources/resourceGroups', targetResourceGroupName)

@description('The name of the resource group.')
output resource_group_name string = targetResourceGroupName

@description('The resource ID of the Application Insights instance.')
output application_insights_id string = monitoring.outputs.applicationInsightsId

@description('The resource ID of the Log Analytics workspace.')
output log_analytics_workspace_id string = monitoring.outputs.logAnalyticsWorkspaceId

@description('The resource ID of the AI Foundry Project.')
output ai_foundry_default_project_id string = defaultProject.outputs.projectId

@description('The name of the AI Foundry Project.')
output ai_foundry_default_project_name string = defaultProject.outputs.projectName

@description('The principal ID of the AI Foundry project system-assigned managed identity.')
output ai_foundry_default_project_identity_principal_id string = defaultProject.outputs.projectPrincipalId
