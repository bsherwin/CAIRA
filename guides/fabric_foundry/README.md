# Fabric Foundry Integration

This guide demonstrates how to automate the integration between Microsoft Fabric Data Agents and Azure AI Foundry.

## Overview

The automation script performs the following steps:

1. **Upload Notebook**: Uploads the `create_fabric_data_agent.ipynb` notebook to a specified Fabric workspace
1. **Execute Notebook**: Triggers the notebook to run, which creates a Fabric Data Agent named "data_agent_automation_sample"
1. **Retrieve Artifact ID**: Gets the artifact ID of the newly created data agent
1. **Create Connection**: Creates a Connected Resource connection in AI Foundry pointing to the Fabric Data Agent
1. **Create Agent**: Creates an AI Foundry Agent that uses the Fabric Data Agent as a knowledge source via FabricTool

## Prerequisites

- Azure subscription with access to:
  - Microsoft Fabric workspace
  - Azure AI Foundry project (not Hub - must be a Project resource)
  - AI model deployment in AI Foundry project (e.g., gpt-4o)
- Fabric workspace must have:
  - NYC Taxi lakehouse named "NYCTaxi_756" with tables: year_2017, year_2018, year_2019, year_2020
  - Active capacity (required for notebook execution)
- Azure CLI or DefaultAzureCredential authentication configured
- Python 3.12 or higher
- uv package manager installed

## Setup

1. Install dependencies using uv:

```bash
cd guides/fabric_foundry
uv sync
```

1. Create a `.env` file with required environment variables:

```bash
# Fabric Configuration
FABRIC_WORKSPACE_ID=your-fabric-workspace-id

# Azure AI Foundry Configuration
AI_FOUNDRY_SUBSCRIPTION_ID=your-subscription-id
AI_FOUNDRY_RESOURCE_GROUP=your-resource-group
AI_FOUNDRY_ACCOUNT_NAME=your-ai-foundry-account-name
AI_FOUNDRY_PROJECT_NAME=your-ai-foundry-project-name
AI_FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
```

**Note**: Replace `AI_FOUNDRY_MODEL_DEPLOYMENT_NAME` with your actual model deployment name from the "Models + endpoints" tab in your AI Foundry project.

## Usage

Run the automation script:

```bash
uv run python automate_fabric_foundry_integration.py
```

The script will:

- Load configuration from `.env` file
- Authenticate using DefaultAzureCredential
- Upload and execute the notebook in Fabric (or reuse existing notebook)
- Wait for completion (up to 10 minutes)
- Create the Fabric connection in AI Foundry using ARM REST API
- Create an AI Foundry Agent with FabricTool using Azure AI Projects SDK
- Output the created resource IDs

## Debugging

To debug the script in VS Code:

1. The `.vscode/launch.json` is configured to use the uv virtual environment
1. Set breakpoints in the script
1. Press F5 or use "Run and Debug" to start debugging

## Implementation Notes

### Connection Creation

- Uses Azure Resource Manager REST API (`Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01`)
- Connection category: `CustomKeys`
- Authentication type: `CustomKeys`
- Stores workspace ID, artifact ID, and type in credentials

### Agent Creation

- Uses Azure AI Projects Python SDK (`azure-ai-projects>=1.0.0b1`)
- Uses Azure AI Agents SDK (`azure-ai-agents>=1.2.0b6`) for FabricTool
- FabricTool connects the agent to the Fabric Data Agent as a knowledge source
- Requires valid model deployment name from AI Foundry project

## Files

- `create_fabric_data_agent.ipynb`: Notebook that creates the Fabric Data Agent (must be run in Fabric)
- `automate_fabric_foundry_integration.py`: Main automation script
- `requirements.txt`: Python dependencies
- `.env`: Environment configuration (not committed to git)
- `README.md`: This file

## Dependencies

Key Python packages:

- `azure-identity>=1.15.0` - Azure authentication
- `requests>=2.31.0` - HTTP requests for Fabric and ARM APIs
- `python-dotenv>=1.0.0` - Environment variable management
- `azure-ai-projects>=1.0.0b1` - AI Foundry Projects SDK
- `azure-ai-agents>=1.2.0b6` - AI Agents SDK with FabricTool support

## Troubleshooting

### CapacityNotActive Error

If you get this error when triggering notebook execution, ensure your Fabric workspace has an active capacity assigned.

### 404 Resource Not Found (Agent Creation)

Verify that `AI_FOUNDRY_MODEL_DEPLOYMENT_NAME` matches exactly with a deployment name in your AI Foundry project's "Models + endpoints" tab.

### Import Errors

Make sure you're using the preview version of `azure-ai-agents` (1.2.0b6 or higher) which includes FabricTool:

```bash
uv pip install --pre --upgrade azure-ai-agents
```

## Notes

- The Fabric Data Agent SDK can only run inside Microsoft Fabric environments
- The automation uses the Fabric REST API to upload and trigger notebook execution
- The script waits up to 10 minutes for notebook completion with 10-second polling intervals
- Notebooks are reused if they already exist (prevents duplicate creation errors)
- All resources are created with simple configurations suitable for POC/demo purposes
- This is a proof-of-concept implementation - keep it simple!
