targetScope = 'resourceGroup'

@minLength(8)
param name string
param location string = resourceGroup().location
param tags object = {}
@secure()
param authSecret string

@secure()
param adminPassword string

param adminUsername string
param foundryProjectEndpoint string
param foundryModel string
param eventhouseUri string
param eventhouseDb string
param lakehouseSqlEndpoint string
param lakehouseDb string
param sportsIqSport string

var suffix = take(uniqueString(subscription().id, resourceGroup().id, name), 8)
var registryName = toLower(take('sportsiq${suffix}registry', 24))
var storageName = toLower(take('stsportsiq${suffix}', 24))
var agentsServiceName = 'agents'
var webappServiceName = 'webapp'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${name}'
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${name}'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    policies: {
      retentionPolicy: {
        days: 7
        status: 'enabled'
      }
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take('kv-${name}-${suffix}', 24)
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${name}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource agents 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${name}-agents'
  location: location
  tags: union(tags, {
    'azd-service-name': agentsServiceName
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          name: agentsServiceName
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'FOUNDRY_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
            { name: 'FOUNDRY_MODEL', value: foundryModel }
            { name: 'EVENTHOUSE_URI', value: eventhouseUri }
            { name: 'EVENTHOUSE_DB', value: eventhouseDb }
            { name: 'LAKEHOUSE_SQL_ENDPOINT', value: lakehouseSqlEndpoint }
            { name: 'LAKEHOUSE_DB', value: lakehouseDb }
            { name: 'LAKEHOUSE_SCHEMA', value: 'dbo' }
            { name: 'SPORTS_IQ_SPORT', value: sportsIqSport }
            { name: 'AZURE_TABLE_STORAGE_ENDPOINT', value: storage.properties.primaryEndpoints.table }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
            { name: 'CORS_ALLOWED_ORIGINS', value: 'http://localhost:3000' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

resource webapp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${name}-web'
  location: location
  tags: union(tags, {
    'azd-service-name': webappServiceName
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'auth-secret'
          value: authSecret
        }
        {
          name: 'admin-password'
          value: adminPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: webappServiceName
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'AGENTS_API_URL', value: 'https://${agents.properties.configuration.ingress.fqdn}' }
            { name: 'AUTH_SECRET', secretRef: 'auth-secret' }
            { name: 'ADMIN_USERNAME', value: adminUsername }
            { name: 'ADMIN_PASSWORD', secretRef: 'admin-password' }
            { name: 'SPORTS_IQ_SPORT', value: sportsIqSport }
            { name: 'NODE_ENV', value: 'production' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

var acrPullRole = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)
var storageTableContributorRole = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
)
resource agentsAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, agents.id, acrPullRole)
  scope: registry
  properties: {
    principalId: agents.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRole
  }
}

resource webappAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, webapp.id, acrPullRole)
  scope: registry
  properties: {
    principalId: webapp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRole
  }
}

resource agentsStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, agents.id, storageTableContributorRole)
  scope: storage
  properties: {
    principalId: agents.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageTableContributorRole
  }
}

output containerRegistryEndpoint string = registry.properties.loginServer
output keyVaultName string = vault.name
output logAnalyticsWorkspaceId string = logs.id
output agentsName string = agents.name
output webappName string = webapp.name
output agentsPrincipalId string = agents.identity.principalId
output webUrl string = 'https://${webapp.properties.configuration.ingress.fqdn}'
