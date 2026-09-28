targetScope = 'subscription'

@minLength(2)
@maxLength(20)
param environmentName string
param location string
@secure()
param authSecret string

@secure()
param adminPassword string

param adminUsername string = 'sportsiq-admin'
param foundryProjectEndpoint string
param foundryModel string = 'gpt-4.1'
param eventhouseUri string
param eventhouseDb string = 'SportsIQ_Eventhouse'
param lakehouseSqlEndpoint string
param lakehouseDb string = 'SportsIQ_Lakehouse'
param sportsIqSport string = 'basketball'

var suffix = take(uniqueString(subscription().id, environmentName, location), 6)
var tags = {
  'azd-env-name': environmentName
  solution: 'sportsiq'
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources './modules/resources.bicep' = {
  name: 'sportsiq-resources'
  scope: resourceGroup
  params: {
    name: 'sportsiq-${environmentName}-${suffix}'
    location: location
    tags: tags
    authSecret: authSecret
    adminUsername: adminUsername
    adminPassword: adminPassword
    foundryProjectEndpoint: foundryProjectEndpoint
    foundryModel: foundryModel
    eventhouseUri: eventhouseUri
    eventhouseDb: eventhouseDb
    lakehouseSqlEndpoint: lakehouseSqlEndpoint
    lakehouseDb: lakehouseDb
    sportsIqSport: sportsIqSport
  }
}

output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.containerRegistryEndpoint
output AZURE_KEY_VAULT_NAME string = resources.outputs.keyVaultName
output AZURE_LOG_ANALYTICS_WORKSPACE_ID string = resources.outputs.logAnalyticsWorkspaceId
output SERVICE_AGENTS_NAME string = resources.outputs.agentsName
output SERVICE_WEBAPP_NAME string = resources.outputs.webappName
output AGENTS_IDENTITY_PRINCIPAL_ID string = resources.outputs.agentsPrincipalId
output WEB_URL string = resources.outputs.webUrl
