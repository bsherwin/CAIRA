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
import sys
import time
import base64
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
FABRIC_DATA_AGENT_NAME = "data_agent_automation_sample"
AI_FOUNDRY_API_VERSION = "2025-06-01"
NOTEBOOK_POLL_INTERVAL = 10
NOTEBOOK_TIMEOUT = 600


class FabricFoundryIntegration:
    """Handles integration between Microsoft Fabric and Azure AI Foundry."""

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
        self._fabric_token = None
        self._arm_token = None

    # ============================================================================
    # Authentication Helpers
    # ============================================================================

    def _get_fabric_token(self) -> str:
        """Get or refresh authentication token for Fabric APIs."""
        if not self._fabric_token:
            token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
            self._fabric_token = token.token
        return self._fabric_token

    def _get_arm_token(self) -> str:
        """Get or refresh authentication token for Azure Resource Manager APIs."""
        if not self._arm_token:
            token = self.credential.get_token("https://management.azure.com/.default")
            self._arm_token = token.token
        return self._arm_token

    def _get_fabric_headers(self) -> Dict[str, str]:
        """Get headers for Fabric API requests."""
        return {
            "Authorization": f"Bearer {self._get_fabric_token()}",
            "Content-Type": "application/json",
        }

    def _get_arm_headers(self) -> Dict[str, str]:
        """Get headers for ARM API requests."""
        return {
            "Authorization": f"Bearer {self._get_arm_token()}",
            "Content-Type": "application/json",
        }

    # ============================================================================
    # Fabric Notebook Operations
    # ============================================================================

    def _find_existing_notebook(self, notebook_name: str) -> Optional[str]:
        """Check if notebook with given name already exists in workspace."""
        try:
            list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/items"
            response = requests.get(list_url, headers=self._get_fabric_headers())
            response.raise_for_status()
            items = response.json().get("value", [])

            for item in items:
                if item.get("displayName") == notebook_name and item.get("type") == "Notebook":
                    return item["id"]
            return None
        except requests.exceptions.RequestException as e:
            print(f"⚠ Warning: Could not check for existing notebook: {e}")
            return None

    def _create_notebook(self, notebook_path: str, notebook_name: str) -> str:
        """Create a new notebook in Fabric workspace."""
        with open(notebook_path, "rb") as f:
            notebook_content = base64.b64encode(f.read()).decode("utf-8")

        create_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/items"
        payload = {
            "displayName": notebook_name,
            "type": "Notebook",
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

        response = requests.post(create_url, headers=self._get_fabric_headers(), json=payload)
        if not response.ok:
            raise Exception(f"Failed to create notebook: {response.status_code} - {response.text}")

        response_data = response.json()
        if not response_data or "id" not in response_data:
            raise ValueError("Response missing 'id' field")

        return response_data["id"]

    def upload_notebook(self, notebook_path: str, notebook_name: str) -> str:
        """Upload notebook to Fabric workspace, reusing if it already exists."""
        # Check if notebook already exists
        existing_id = self._find_existing_notebook(notebook_name)
        if existing_id:
            print(f"✓ Found existing notebook '{notebook_name}' with ID: {existing_id}")
            return existing_id

        # Create new notebook
        notebook_id = self._create_notebook(notebook_path, notebook_name)
        print(f"✓ Uploaded notebook '{notebook_name}' with ID: {notebook_id}")
        return notebook_id

    def trigger_notebook_run(self, notebook_id: str) -> str:
        """Trigger notebook execution and return job ID."""
        run_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"

        response = requests.post(run_url, headers=self._get_fabric_headers())
        if not response.ok:
            raise Exception(f"Failed to trigger notebook: {response.status_code} - {response.text}")

        # Handle 202 Accepted response
        if response.status_code == 202:
            location = response.headers.get("Location", "")
            if location:
                job_id = location.split("/")[-1]
                print(f"✓ Triggered notebook run with job ID: {job_id}")
                return job_id

            # Fallback: query for most recent job
            print(f"✓ Notebook run triggered (202 Accepted), retrieving job ID...")
            time.sleep(2)
            jobs_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/notebooks/{notebook_id}/jobs/instances"
            jobs_response = requests.get(jobs_url, headers=self._get_fabric_headers())
            jobs_response.raise_for_status()
            jobs = jobs_response.json().get("value", [])
            if jobs:
                job_id = jobs[0]["id"]
                print(f"✓ Found running job with ID: {job_id}")
                return job_id
            raise ValueError("Notebook run triggered but no job ID found")

        # Normal response with body
        response_data = response.json()
        job_id = response_data["id"]
        print(f"✓ Triggered notebook run with job ID: {job_id}")
        return job_id

    def wait_for_notebook_completion(self, notebook_id: str, job_id: str) -> bool:
        """Wait for notebook execution to complete."""
        status_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/notebooks/{notebook_id}/jobs/instances/{job_id}"

        start_time = time.time()
        while time.time() - start_time < NOTEBOOK_TIMEOUT:
            try:
                response = requests.get(status_url, headers=self._get_fabric_headers())
                response.raise_for_status()
                status = response.json()["status"]

                if status == "Completed":
                    print("✓ Notebook execution completed successfully")
                    return True
                elif status in ["Failed", "Cancelled"]:
                    print(f"✗ Notebook execution {status}")
                    return False

                print(f"  Notebook status: {status}, waiting...")
                time.sleep(NOTEBOOK_POLL_INTERVAL)
            except requests.exceptions.RequestException as e:
                print(f"⚠ Warning: Error checking notebook status: {e}")
                time.sleep(NOTEBOOK_POLL_INTERVAL)

        print("✗ Timeout waiting for notebook completion")
        return False

    # ============================================================================
    # Fabric Data Agent Operations
    # ============================================================================

    def get_data_agent_artifact_id(self, data_agent_name: str) -> Optional[str]:
        """Retrieve the artifact ID of the created Fabric Data Agent."""
        try:
            list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/items"
            response = requests.get(list_url, headers=self._get_fabric_headers())
            response.raise_for_status()
            items = response.json().get("value", [])

            for item in items:
                if item.get("displayName") == data_agent_name:
                    item_id = item["id"]

                    # Get full item details
                    get_item_url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.fabric_workspace_id}/items/{item_id}"
                    item_response = requests.get(get_item_url, headers=self._get_fabric_headers())
                    item_response.raise_for_status()
                    item_details = item_response.json()

                    artifact_id = item_details["id"]
                    print(f"✓ Found data agent '{data_agent_name}' with artifact ID: {artifact_id}")
                    return artifact_id

            print(f"✗ Data agent '{data_agent_name}' not found")
            return None
        except requests.exceptions.RequestException as e:
            print(f"✗ Error retrieving data agent: {e}")
            return None

    # ============================================================================
    # AI Foundry Operations
    # ============================================================================

    def _build_connection_url(self, connection_name: str) -> str:
        """Build the ARM URL for AI Foundry Project connection."""
        return (
            f"https://management.azure.com/subscriptions/{self.ai_foundry_subscription_id}"
            f"/resourceGroups/{self.ai_foundry_resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{self.ai_foundry_account_name}"
            f"/projects/{self.ai_foundry_project_name}"
            f"/connections/{connection_name}"
            f"?api-version={AI_FOUNDRY_API_VERSION}"
        )

    def _build_agent_url(self, agent_name: str) -> str:
        """Build the ARM URL for AI Foundry Project agent."""
        return (
            f"https://management.azure.com/subscriptions/{self.ai_foundry_subscription_id}"
            f"/resourceGroups/{self.ai_foundry_resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{self.ai_foundry_account_name}"
            f"/projects/{self.ai_foundry_project_name}"
            f"/agents/{agent_name}"
            f"?api-version={AI_FOUNDRY_API_VERSION}"
        )

    def create_foundry_to_fabric_connection(self, data_agent_artifact_id: str) -> str:
        """Create a Connected Resource connection in AI Foundry Project to Fabric."""
        connection_name = "fabric-data-agent-connection"
        connection_url = self._build_connection_url(connection_name)

        connection_payload = {
            "properties": {
                "category": "CustomKeys",
                "authType": "CustomKeys",
                "credentials": {
                    "keys": {
                        "workspace-id": self.fabric_workspace_id,
                        "artifact-id": data_agent_artifact_id,
                        "type": "fabric_dataagent"
                    }
                },
            }
        }

        response = requests.put(connection_url, headers=self._get_arm_headers(), json=connection_payload)
        if not response.ok:
            raise Exception(f"Failed to create connection: {response.status_code} - {response.text}")

        print(f"✓ Created Fabric connection: {connection_name}")
        return connection_name

    def create_ai_foundry_agent(self, connection_name: str) -> str:
        """Create an AI Foundry Agent using the Fabric connection as knowledge source."""
        agent_name = "fabric-data-agent"
        agent_url = self._build_agent_url(agent_name)

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

        response = requests.put(agent_url, headers=self._get_arm_headers(), json=agent_payload)
        if not response.ok:
            raise Exception(f"Failed to create agent: {response.status_code} - {response.text}")

        agent_id = response.json().get("id", agent_name)
        print(f"✓ Created AI Foundry Agent with ID: {agent_id}")
        return agent_id


# ============================================================================
# Main Execution
# ============================================================================

def validate_environment() -> Dict[str, str]:
    """Validate and return required environment variables."""
    required_vars = {
        "FABRIC_WORKSPACE_ID": os.getenv("FABRIC_WORKSPACE_ID", ""),
        "AI_FOUNDRY_SUBSCRIPTION_ID": os.getenv("AI_FOUNDRY_SUBSCRIPTION_ID", ""),
        "AI_FOUNDRY_RESOURCE_GROUP": os.getenv("AI_FOUNDRY_RESOURCE_GROUP", ""),
        "AI_FOUNDRY_ACCOUNT_NAME": os.getenv("AI_FOUNDRY_ACCOUNT_NAME", ""),
        "AI_FOUNDRY_PROJECT_NAME": os.getenv("AI_FOUNDRY_PROJECT_NAME", ""),
    }

    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        print("✗ Error: Required environment variables not set:")
        for var in missing_vars:
            print(f"  - {var}")
        sys.exit(1)

    return required_vars


def main():
    """Main execution flow."""
    print("Starting Fabric-Foundry integration automation...")
    print("=" * 60)

    # Validate environment
    env_vars = validate_environment()

    # Initialize integration
    try:
        integration = FabricFoundryIntegration(
            fabric_workspace_id=env_vars["FABRIC_WORKSPACE_ID"],
            ai_foundry_subscription_id=env_vars["AI_FOUNDRY_SUBSCRIPTION_ID"],
            ai_foundry_resource_group=env_vars["AI_FOUNDRY_RESOURCE_GROUP"],
            ai_foundry_account_name=env_vars["AI_FOUNDRY_ACCOUNT_NAME"],
            ai_foundry_project_name=env_vars["AI_FOUNDRY_PROJECT_NAME"],
        )
    except Exception as e:
        print(f"✗ Error initializing integration: {e}")
        sys.exit(1)

    try:
        # Step 1: Upload notebook
        print("\n[Step 1/5] Uploading notebook...")
        notebook_path = "create_fabric_data_agent.ipynb"
        notebook_id = integration.upload_notebook(notebook_path, "create_fabric_data_agent")

        # Step 2: Trigger notebook run
        print("\n[Step 2/5] Triggering notebook execution...")
        job_id = integration.trigger_notebook_run(notebook_id)

        # Step 3: Wait for completion
        print("\n[Step 3/5] Waiting for notebook completion...")
        if not integration.wait_for_notebook_completion(notebook_id, job_id):
            print("✗ Notebook execution failed, aborting")
            sys.exit(1)

        # Step 4: Retrieve data agent artifact ID
        print("\n[Step 4/5] Retrieving data agent artifact ID...")
        data_agent_artifact_id = integration.get_data_agent_artifact_id(FABRIC_DATA_AGENT_NAME)
        if not data_agent_artifact_id:
            print("✗ Could not retrieve data agent artifact ID, aborting")
            sys.exit(1)

        # Step 5: Create Fabric connection in AI Foundry Project
        print("\n[Step 5/5] Creating AI Foundry connection and agent...")
        connection_name = integration.create_foundry_to_fabric_connection(data_agent_artifact_id)

        # Step 6: Create AI Foundry Agent
        agent_id = integration.create_ai_foundry_agent(connection_name)

        # Success summary
        print("\n" + "=" * 60)
        print("✓ Integration complete!")
        print(f"  - Data Agent Artifact ID: {data_agent_artifact_id}")
        print(f"  - Connection Name: {connection_name}")
        print(f"  - Agent ID: {agent_id}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n✗ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
