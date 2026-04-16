import os
import yaml
import json
import requests
from typing import List, Dict, Any, Optional
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

    def _get_public_url(self) -> Optional[str]:
        """Fetch the public URL from the ngrok container's API."""
        try:
            # We use 'ngrok' as the hostname since it's the service name in docker-compose
            response = requests.get("http://ngrok:4040/api/tunnels", timeout=2)
            if response.ok:
                tunnels = response.json().get("tunnels", [])
                # Look for the https tunnel
                https_tunnel = next((t for t in tunnels if t.get("proto") == "https"), None)
                if https_tunnel:
                    return https_tunnel.get("public_url")
        except Exception as e:
            print(f"⚠️  Could not detect ngrok tunnel: {e}")
        return None

    def provision_famiglia(self, app_level_token: str = None) -> List[Dict[str, Any]]:
        """
        Create Slack apps for the entire Famiglia roster.
        """
        if not app_level_token:
            # Fallback to DB stored token if not provided in payload
            conn = user_connections_store.get_connection("slack_bootstrap")
            if conn:
                app_level_token = conn["access_token"]
        
        if not app_level_token:
            raise ValueError("No Slack App Configuration Token found. Please provide one in the setup.")

        manifest_dir = os.path.join(os.path.dirname(__file__), "app_manifest")
        manifest_files = [os.path.join(manifest_dir, f) for f in os.listdir(manifest_dir) if f.endswith(".yaml") or f.endswith(".yml")]
        
        client = WebClient(token=app_level_token)
        provisioned_apps = []

        # Detect public URL for Choice B (Total Automation)
        public_url = self._get_public_url()
        if public_url:
            print(f"🌐 Detected Public Tunnel: {public_url}")
        else:
            print("💡 No public tunnel detected. Falling back to Socket Mode (Semi-Automated).")

        for manifest_path in manifest_files:
            filename = os.path.basename(manifest_path)
            if filename == "passione_famiglia.yaml": # Global manifest, skip for individual agents
                continue
                
            agent_id = filename.replace(".yaml", "").replace(".yml", "")
            
            with open(manifest_path, 'r') as f:
                try:
                    manifest_data = yaml.safe_load(f)
                    
                    # TOTAL AUTOMATION INJECTION (Choice B)
                    # If we have a public URL, we flip the app to HTTP mode
                    if public_url:
                        # 1. Disable Socket Mode
                        if 'settings' not in manifest_data:
                            manifest_data['settings'] = {}
                        manifest_data['settings']['socket_mode_enabled'] = False
                        
                        # 2. Set Redirect URI for OAuth bridge
                        callback_url = f"{public_url}/api/v1/connections/auth/slack/agent/callback"
                        if 'oauth_config' not in manifest_data:
                             manifest_data['oauth_config'] = {}
                        manifest_data['oauth_config']['redirect_urls'] = [callback_url]
                        
                        # 3. Set Request URLs for Events & Interactivity
                        events_url = f"{public_url}/api/v1/comms/slack/events/{agent_id}"
                        if 'event_subscriptions' not in manifest_data['settings']:
                            manifest_data['settings']['event_subscriptions'] = {}
                        manifest_data['settings']['event_subscriptions']['request_url'] = events_url
                        
                        if 'interactivity' not in manifest_data['settings']:
                             manifest_data['settings']['interactivity'] = {}
                        manifest_data['settings']['interactivity']['request_url'] = events_url

                    # Strip experimental/beta fields that might trigger 'not_allowed_token_type'
                    if 'settings' in manifest_data:
                        manifest_data['settings'].pop('is_mcp_enabled', None)

                    # Convert to JSON string for API
                    manifest_str = json.dumps(manifest_data)
                except yaml.YAMLError:
                    print(f"Error parsing manifest: {filename}")
                    continue

            try:
                # DEDUPLICATION: Check if this agent has already been provisioned
                existing_creds = user_connections_store.get_connection(f"slack_creds:{agent_id}")
                app_id = None
                creds = {}
                
                if existing_creds:
                    try:
                        data = json.loads(existing_creds["access_token"])
                        app_id = data.get("app_id")
                        creds = {
                            "client_id": data.get("client_id"),
                            "client_secret": data.get("client_secret"),
                        }
                    except Exception:
                        pass

                if app_id:
                    print(f"🔄 Syncing existing {agent_id} (App ID: {app_id})...")
                    response = client.apps_manifest_update(app_id=app_id, manifest=manifest_str)
                else:
                    print(f"📦 Manifesting new {agent_id}...")
                    response = client.apps_manifest_create(manifest=manifest_str)
                
                if response["ok"]:
                    # Create case returns app_id and credentials
                    # Update case only returned ok: True
                    if not app_id:
                        app_id = response["app_id"]
                        creds = response.get("credentials", {})
                    
                    # SECURE STORAGE: Save/Update IDs and Secrets
                    user_connections_store.upsert_connection(
                        service=f"slack_creds:{agent_id}",
                        access_token=json.dumps({
                            "client_id": creds.get("client_id"),
                            "client_secret": creds.get("client_secret"),
                            "app_id": app_id
                        }),
                        username=manifest_data["display_information"]["name"]
                    )

                    # Construct Install URL
                    if public_url:
                        # Direct to our bridge
                        install_url = f"https://slack.com/oauth/v2/authorize?client_id={creds.get('client_id')}&scope=app_mentions:read,chat:write,channels:history,groups:history,im:history,reactions:write&state={agent_id}"
                    else:
                        install_url = f"https://api.slack.com/apps/{app_id}/install"

                    app_info = {
                        "agent_id": agent_id,
                        "name": manifest_data["display_information"]["name"],
                        "app_id": app_id,
                        "install_url": install_url
                    }
                    provisioned_apps.append(app_info)
                    status_icon = "✅ Updated" if existing_creds else "✅ Created"
                    print(f"{status_icon} {agent_id} (App ID: {app_id})")
                else:
                    print(f"❌ Failed to process {agent_id}: {response['error']}")
                    print(f"   Full Response: {response}")
            except SlackApiError as e:
                print(f"❌ Slack API Error for {agent_id}: {e.response['error']}")
            except Exception as e:
                print(f"❌ Unexpected error manifesting {agent_id}: {e}")
                
        return provisioned_apps

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
