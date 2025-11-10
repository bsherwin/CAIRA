# Fabric Foundry Integration

This guide demonstrates how to automate the integration between Microsoft Fabric Data Agents and Azure AI Foundry.

## Overview

The automation script performs the following steps:

1. **Upload Notebook**: Uploads the `create_fabric_data_agent.ipynb` notebook to a specified Fabric workspace
1. **Execute Notebook**: Triggers the notebook to run, which creates a Fabric Data Agent named "data_agent_automation_sample"
1. **Retrieve Artifact ID**: Gets the artifact ID of the newly created data agent
1. **Create Connection**: Creates a Connected Resource connection in AI Foundry pointing to the Fabric Data Agent
1. **Create Agent**: Creates an AI Foundry Agent that uses the Fabric Data Agent as a knowledge source

## Prerequisites

- Azure subscription with access to:
  - Microsoft Fabric workspace
  - Azure AI Foundry project (not Hub - must be a Project resource)
- Fabric workspace must have:
  - NYC Taxi lakehouse named "NYCTaxi_756" with tables: year_2017, year_2018, year_2019, year_2020
- Azure CLI or DefaultAzureCredential authentication configured
- Python 3.8 or higher

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Set required environment variables:

```bash
export FABRIC_WORKSPACE_ID="your-fabric-workspace-id"
export AI_FOUNDRY_SUBSCRIPTION_ID="your-subscription-id"
export AI_FOUNDRY_RESOURCE_GROUP="your-resource-group"
export AI_FOUNDRY_ACCOUNT_NAME="your-ai-foundry-account-name"
export AI_FOUNDRY_PROJECT_NAME="your-ai-foundry-project-name"
```

## Usage

Run the automation script:

```bash
python automate_fabric_foundry_integration.py
```

The script will:

- Authenticate using DefaultAzureCredential
- Upload and execute the notebook in Fabric
- Wait for completion
- Create the necessary connections and agent in AI Foundry Project using ARM REST APIs
- Output the created resource IDs

## Implementation Notes

- Uses Azure Resource Manager REST API (`Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01`) for creating connections
- Uses Azure Resource Manager REST API for creating agents in AI Foundry Projects
- No Python SDK dependency for AI Foundry - direct REST API calls for maximum compatibility

## Files

- `create_fabric_data_agent.ipynb`: Notebook that creates the Fabric Data Agent (must be run in Fabric)
- `automate_fabric_foundry_integration.py`: Main automation script
- `requirements.txt`: Python dependencies
- `README.md`: This file

## Notes

- The Fabric Data Agent SDK can only run inside Microsoft Fabric environments
- The automation uses the Fabric REST API to upload and trigger notebook execution
- The script waits up to 10 minutes for notebook completion
- All resources are created with simple configurations suitable for POC/demo purposes
