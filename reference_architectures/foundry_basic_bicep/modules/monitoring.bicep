targetScope = 'resourceGroup'

@description('Location for all resources.')
param location string

@description('Tags to be applied to resources.')
param tags object = {}

@description('Name of the Log Analytics workspace.')
param logAnalyticsWorkspaceName string

@description('Name of the Application Insights instance.')
param applicationInsightsName string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  tags: tags
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: logAnalytics.id
    Request_Source: 'rest'
  }
}

@description('The resource ID of the Log Analytics workspace.')
output logAnalyticsWorkspaceId string = logAnalytics.id

@description('The resource ID of the Application Insights instance.')
output applicationInsightsId string = applicationInsights.id

@description('The name of the Application Insights instance.')
output applicationInsightsName string = applicationInsights.name

@description('Application Insights Connection String.')
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
