import os
import yaml
import glob
from typing import List, Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from famiglia_core.db.tools.user_connections_store import user_connections_store

class SlackProvisioningService:
    """
    Automates the creation and configuration of the Famiglia agent bots.
    """
    
    def __init__(self):
        self.manifest_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "app_manifest"
        )

    def provision_famiglia(self, app_level_token: str) -> List[Dict[str, Any]]:
        """
        Creates all agent apps in the user's workspace using the provided token.
        Returns a list of created apps with their credentials and install URLs.
        """
        client = WebClient(token=app_level_token)
        manifest_files = glob.glob(os.path.join(self.manifest_dir, "*.yaml"))
        
        results = []
        
        for manifest_path in manifest_files:
            filename = os.path.basename(manifest_path)
            if filename == "passione_famiglia.yaml": # Global manifest, skip for individual agents
                continue
                
            agent_id = filename.replace(".yaml", "")
            
            with open(manifest_path, 'r') as f:
                try:
                    manifest_data = yaml.safe_load(f)
                    # Convert to string for API
                    manifest_str = yaml.dump(manifest_data)
                except yaml.YAMLError:
                    print(f"Error parsing manifest: {filename}")
                    continue

            try:
                # Create the app
                response = client.apps_manifest_create(manifest=manifest_str)
                
                if response["ok"]:
                    app_id = response["app_id"]
                    creds = response["credentials"]
                    
                    # Store app metadata in DB (service name like 'slack_app:alfredo')
                    user_connections_store.upsert_connection(
                        service=f"slack_app:{agent_id}",
                        access_token=app_id, # Reusing access_token field for app_id
                        username=manifest_data['display_information']['name'],
                        scopes=yaml.dump(creds) # Store credentials as "scopes" for now
                    )
                    
                    results.append({
                        "agent_id": agent_id,
                        "name": manifest_data['display_information']['name'],
                        "app_id": app_id,
                        "client_id": creds["client_id"],
                        "install_url": f"https://api.slack.com/apps/{app_id}/install-on-team"
                    })
                else:
                    print(f"Failed to create {agent_id}: {response['error']}")
            except SlackApiError as e:
                print(f"Slack API Error during provisioning: {e}")
                
        return results

    def finalize_agent(self, agent_id: str, bot_token: str, app_token: str) -> bool:
        """
        Stores the final tokens for an agent and activates the connection.
        """
        # Store Bot Token
        bot_success = user_connections_store.upsert_connection(
            service=f"slack_bot:{agent_id}",
            access_token=bot_token
        )
        
        # Store App-Level Token (for Socket Mode)
        app_success = user_connections_store.upsert_connection(
            service=f"slack_socket:{agent_id}",
            access_token=app_token
        )
        
        return bot_success and app_success

slack_provisioning = SlackProvisioningService()
