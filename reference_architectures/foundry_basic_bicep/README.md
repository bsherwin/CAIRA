# Foundry Basic (Bicep)

This reference architecture is the Bicep equivalent of `reference_architectures/foundry_basic` (Terraform). It deploys an Azure AI Foundry account (Azure AI Services), a default project, and a monitoring stack (Log Analytics + workspace-based Application Insights).

## Scope

- Deployment scope: **subscription**
- Resource scope: resources are deployed into a single resource group

## What it deploys

- Resource group (optional; created if you do not provide an existing resource group resource ID)
- Log Analytics workspace
- Application Insights (workspace-based)
- Azure AI Foundry account (`Microsoft.CognitiveServices/accounts`, `kind = AIServices`)
- Model deployments:
  - `gpt-4.1@2025-04-14`
  - `o4-mini@2025-04-16`
  - `text-embedding-3-large@1`
- Default AI Foundry project (`Microsoft.CognitiveServices/accounts/projects`)
- AI Foundry connection to Application Insights (`Microsoft.CognitiveServices/accounts/connections`)

## Naming

Names are deterministic and include a 5-character suffix derived from `uniqueString(subscription().id, 'basic', location)`.

## Parameters

- `location` (string): Azure region (default: `swedencentral`)
- `resourceGroupName` (string): Resource group name. If empty, a new resource group is created.
- `sku` (string): AI Foundry SKU (default: `S0`)
- `restoreAiFoundryAccount` (bool): Set to `true` if the AI Foundry account name is currently soft-deleted and you want to restore it.
- `enableTelemetry` (bool): Included for parity with Terraform. This template does not emit AVM telemetry.
- `tags` (object): Optional tags applied to resources

## Deploy

1. Deploy to the subscription:

```bash
az deployment sub create \
  --location swedencentral \
  --template-file reference_architectures/foundry_basic_bicep/main.bicep
```

1. Deploy into an existing resource group by passing its name:

```bash
az deployment sub create \
  --location swedencentral \
  --template-file reference_architectures/foundry_basic_bicep/main.bicep \
  --parameters resourceGroupName="<rgName>"
```

1. Deploy using the included example parameters file:

```bash
az deployment sub create \
  --location swedencentral \
  --template-file reference_architectures/foundry_basic_bicep/main.bicep \
  --parameters @reference_architectures/foundry_basic_bicep/parameters.example.json
```

## Outputs

- `ai_foundry_id`, `ai_foundry_name`, `ai_foundry_endpoint`
- `ai_foundry_model_deployments_ids`
- `ai_foundry_default_project_id`, `ai_foundry_default_project_name`, `ai_foundry_default_project_identity_principal_id`
- `resource_group_id`, `resource_group_name`
- `application_insights_id`, `log_analytics_workspace_id`
