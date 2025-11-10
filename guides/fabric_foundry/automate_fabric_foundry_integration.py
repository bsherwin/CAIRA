#!/usr/bin/env python3
"""
Automate connecting AI Foundry to Microsoft Fabric via Fabric Data Agent.

This script:
1. Uploads the create_fabric_data_agent notebook to a Fabric workspace
2. Triggers notebook execution to create the data agent
3. Retrieves the artifact ID of the created data agent
4. Creates a Connected Resource connection in AI Foundry to Fabric
5. Creates an AI Foundry Agent using this connection as a knowledge source
"""

import os
import time
from typing import Optional
from azure.identity import DefaultAzureCredential
import requests


class FabricFoundryIntegration:
    def __init__(
        self,
        fabric_workspace_id: str,
        ai_foundry_subscription_id: str,
        ai_foundry_resource_group: str,
        ai_foundry_account_name: str,
        ai_foundry_project_name: str,
    ):
        self.fabric_workspace_id = fabric_workspace_id
        self.ai_foundry_subscription_id = ai_foundry_subscription_id
        self.ai_foundry_resource_group = ai_foundry_resource_group
        self.ai_foundry_account_name = ai_foundry_account_name
        self.ai_foundry_project_name = ai_foundry_project_name
        self.credential = DefaultAzureCredential()
        self.fabric_token = None

    def get_fabric_token(self) -> str:
        """Get authentication token for Fabric APIs."""
        token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
        return token.token

    def upload_notebook(self, notebook_path: str, notebook_name: str) -> str:
        """Upload notebook to Fabric workspace and return artifact ID."""
        self.fabric_token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {self.fabric_token}",
            "Content-Type": "application/json",
        }

        with open(notebook_path, "r") as f:
            notebook_content = f.read()

        # Create notebook in Fabric workspace
        create_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/notebooks"
        payload = {
            "displayName": notebook_name,
            "definition": {
                "format": "ipynb",
                "parts": [
                    {
                        "path": "notebook-content.ipynb",
                        "payload": notebook_content,
                        "payloadType": "InlineBase64",
                    }
                ],
            },
        }

        response = requests.post(create_url, headers=headers, json=payload)
        response.raise_for_status()
        notebook_id = response.json()["id"]
        print(f"✓ Uploaded notebook '{notebook_name}' with ID: {notebook_id}")
        return notebook_id

    def trigger_notebook_run(self, notebook_id: str) -> str:
        """Trigger notebook execution and return job ID."""
        headers = {
            "Authorization": f"Bearer {self.fabric_token}",
            "Content-Type": "application/json",
        }

        run_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"

        response = requests.post(run_url, headers=headers)
        response.raise_for_status()
        job_id = response.json()["id"]
        print(f"✓ Triggered notebook run with job ID: {job_id}")
        return job_id

    def wait_for_notebook_completion(self, notebook_id: str, job_id: str, timeout: int = 600) -> bool:
        """Wait for notebook execution to complete."""
        headers = {"Authorization": f"Bearer {self.fabric_token}"}
        status_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/notebooks/{notebook_id}/jobs/instances/{job_id}"

        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(status_url, headers=headers)
            response.raise_for_status()
            status = response.json()["status"]

            if status == "Completed":
                print("✓ Notebook execution completed successfully")
                return True
            elif status in ["Failed", "Cancelled"]:
                print(f"✗ Notebook execution {status}")
                return False

            print(f"  Notebook status: {status}, waiting...")
            time.sleep(10)

        print("✗ Timeout waiting for notebook completion")
        return False

    def get_data_agent_artifact_id(self, data_agent_name: str = "data_agent_automation_sample") -> Optional[str]:
        """Retrieve the artifact ID of the created Fabric Data Agent."""
        headers = {"Authorization": f"Bearer {self.fabric_token}"}

        # List all items in the workspace
        list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/items"

        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        items = response.json().get("value", [])

        # Find the DataAgent item by name and type
        for item in items:
            if item.get("displayName") == data_agent_name: # and item.get("type") == "DataAgent"
                item_id = item["id"]

                # Get the specific item to retrieve full details
                get_item_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/items/{item_id}"
                item_response = requests.get(get_item_url, headers=headers)
                item_response.raise_for_status()
                item_details = item_response.json()

                artifact_id = item_details["id"]
                print(f"✓ Found data agent '{data_agent_name}' with artifact ID: {artifact_id}")
                return artifact_id

        print(f"✗ Data agent '{data_agent_name}' not found")
        return None

    def create_fabric_connection(self, data_agent_artifact_id: str) -> str:
        """Create a Connected Resource connection in AI Foundry Project to Fabric."""
        connection_name = "fabric-data-agent-connection"

        # Get ARM token
        arm_token = self.credential.get_token("https://management.azure.com/.default")
        headers = {
            "Authorization": f"Bearer {arm_token.token}",
            "Content-Type": "application/json",
        }

        # Construct AI Foundry Project connection endpoint
        connection_url = (
            f"https://management.azure.com/subscriptions/{self.ai_foundry_subscription_id}"
            f"/resourceGroups/{self.ai_foundry_resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{self.ai_foundry_account_name}"
            f"/projects/{self.ai_foundry_project_name}"
            f"/connections/{connection_name}"
            f"?api-version=2025-06-01"
        )

        # Connection payload for Fabric Data Agent
        connection_payload = {
            "properties": {
                "category": "FabricDataAgent",
                "target": f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/dataAgents/{data_agent_artifact_id}",
                "authType": "CustomKeys",
                "credentials": {
                    "keys": {
                        "workspace-id": self.fabric_workspace_id,
                        "artifact-id": data_agent_artifact_id,
                        "type": "fabric_dataagent"
                    }
                }
            }
        }

        response = requests.put(connection_url, headers=headers, json=connection_payload)
        response.raise_for_status()
        print(f"✓ Created Fabric connection: {connection_name}")
        return connection_name

    def create_ai_foundry_agent(self, connection_name: str) -> str:
        """Create an AI Foundry Agent using the Fabric connection as knowledge source."""

        # Get ARM token
        arm_token = self.credential.get_token("https://management.azure.com/.default")
        headers = {
            "Authorization": f"Bearer {arm_token.token}",
            "Content-Type": "application/json",
        }

        agent_name = "fabric-data-agent"

        # Construct AI Foundry Project agent endpoint
        agent_url = (
            f"https://management.azure.com/subscriptions/{self.ai_foundry_subscription_id}"
            f"/resourceGroups/{self.ai_foundry_resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{self.ai_foundry_account_name}"
            f"/projects/{self.ai_foundry_project_name}"
            f"/agents/{agent_name}"
            f"?api-version=2025-06-01"
        )

        # Agent payload with Fabric Data Agent connection
        agent_payload = {
            "properties": {
                "model": "gpt-4o",
                "instructions": "You are a helpful assistant with access to NYC taxi data through Fabric Data Agent. Help users answer questions about taxi ridership.",
                "tools": [{"type": "code_interpreter"}],
                "toolResources": {
                    "codeInterpreter": {
                        "dataSources": [
                            {
                                "type": "fabric_data_agent",
                                "connectionId": connection_name,
                            }
                        ]
                    }
                },
            }
        }

        response = requests.put(agent_url, headers=headers, json=agent_payload)
        response.raise_for_status()
        agent_id = response.json().get("id", agent_name)
        print(f"✓ Created AI Foundry Agent with ID: {agent_id}")
        return agent_id


def main():
    """Main execution flow."""
    # Configuration - these should be provided as environment variables or arguments
    FABRIC_WORKSPACE_ID = os.getenv("FABRIC_WORKSPACE_ID", "")
    AI_FOUNDRY_SUBSCRIPTION_ID = os.getenv("AI_FOUNDRY_SUBSCRIPTION_ID", "")
    AI_FOUNDRY_RESOURCE_GROUP = os.getenv("AI_FOUNDRY_RESOURCE_GROUP", "")
    AI_FOUNDRY_ACCOUNT_NAME = os.getenv("AI_FOUNDRY_ACCOUNT_NAME", "")
    AI_FOUNDRY_PROJECT_NAME = os.getenv("AI_FOUNDRY_PROJECT_NAME", "")

    if not all([FABRIC_WORKSPACE_ID, AI_FOUNDRY_SUBSCRIPTION_ID, AI_FOUNDRY_RESOURCE_GROUP, AI_FOUNDRY_ACCOUNT_NAME, AI_FOUNDRY_PROJECT_NAME]):
        print("Error: Required environment variables not set:")
        print("  - FABRIC_WORKSPACE_ID")
        print("  - AI_FOUNDRY_SUBSCRIPTION_ID")
        print("  - AI_FOUNDRY_RESOURCE_GROUP")
        print("  - AI_FOUNDRY_ACCOUNT_NAME")
        print("  - AI_FOUNDRY_PROJECT_NAME")
        return

    integration = FabricFoundryIntegration(
        fabric_workspace_id=FABRIC_WORKSPACE_ID,
        ai_foundry_subscription_id=AI_FOUNDRY_SUBSCRIPTION_ID,
        ai_foundry_resource_group=AI_FOUNDRY_RESOURCE_GROUP,
        ai_foundry_account_name=AI_FOUNDRY_ACCOUNT_NAME,
        ai_foundry_project_name=AI_FOUNDRY_PROJECT_NAME,
    )

    print("Starting Fabric-Foundry integration automation...")
    print("=" * 60)

    # Step 1: Upload notebook
    notebook_path = "create_fabric_data_agent.ipynb"
    notebook_id = integration.upload_notebook(notebook_path, "create_fabric_data_agent")

    # Step 2: Trigger notebook run
    job_id = integration.trigger_notebook_run(notebook_id)

    # Wait for completion
    if not integration.wait_for_notebook_completion(notebook_id, job_id):
        print("✗ Notebook execution failed, aborting")
        return

    # Step 3: Retrieve data agent artifact ID
    data_agent_artifact_id = integration.get_data_agent_artifact_id()
    if not data_agent_artifact_id:
        print("✗ Could not retrieve data agent artifact ID, aborting")
        return

    # Step 4: Create Fabric connection in AI Foundry Project
    connection_name = integration.create_fabric_connection(data_agent_artifact_id, AI_FOUNDRY_ACCOUNT_NAME)

    # Step 5: Create AI Foundry Agent
    agent_id = integration.create_ai_foundry_agent(connection_name)

    print("=" * 60)
    print("✓ Integration complete!")
    print(f"  - Data Agent Artifact ID: {data_agent_artifact_id}")
    print(f"  - Connection Name: {connection_name}")
    print(f"  - Agent ID: {agent_id}")


if __name__ == "__main__":
    main()
