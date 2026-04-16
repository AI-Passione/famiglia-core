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
        self.registry = {
            "ALFREDO_COMMAND": {"name": "alfredo-command", "agents": ["alfredo"]},
            "CODE_REVIEWS": {"name": "code-reviews", "agents": ["riccardo"]},
            "DATA_ENGINEERING": {"name": "data-engineering", "agents": ["riccardo"]},
            "DEV_OPS": {"name": "devops", "agents": ["riccardo"]},
            "PROJECTS": {"name": "projects", "agents": ["bella"]},
            "WEEKLY_UPDATES": {"name": "weekly-updates", "agents": ["bella"]},
            "RESEARCH_INSIGHTS": {"name": "research-insights", "agents": ["rossini"]},
            "PRODUCT_STRATEGY": {"name": "product-strategy", "agents": ["rossini"]},
            "MARKETING": {"name": "marketing", "agents": ["rossini", "giuseppina"]},
            "FINANCE": {"name": "finance", "agents": ["vito"]},
            "INVESTMENTS": {"name": "investments", "agents": ["vito"]},
            "OPERATIONS": {"name": "operations", "agents": ["tommy"]},
            "LOGISTICS": {"name": "logistics", "agents": ["tommy"]},
            "ANALYTICS": {"name": "analytics", "agents": ["kowalski"]},
            "DATA_SCIENCE": {"name": "data-science", "agents": ["kowalski"]},
            "TOWNHALL": {"name": "townhall", "agents": ["giuseppina"]},
            "SOCIAL": {"name": "social", "agents": ["giuseppina"]},
            "CORE_FAMIGLIA": {
                "name": "the-famiglia",
                "agents": ["alfredo", "vito", "riccardo", "rossini", "tommy", "bella", "kowalski", "giuseppina"]
            }
        }

    def _get_public_url(self) -> Optional[str]:
        """Fetch the public URL from environment or ngrok container's API."""
        # 1. Check direct environment override first
        env_url = os.getenv("PUBLIC_URL") or os.getenv("SLACK_REDIRECT_HOST")
        if env_url:
            return env_url.rstrip("/")

        # 2. Try to detect from ngrok
        try:
            # We use 'ngrok' as the hostname since it's the service name in docker-compose
            # But we also try 'localhost' if running on host
            for host in ["ngrok", "localhost"]:
                try:
                    response = requests.get(f"http://{host}:4040/api/tunnels", timeout=1)
                    if response.ok:
                        tunnels = response.json().get("tunnels", [])
                        # Look for the https tunnel
                        https_tunnel = next((t for t in tunnels if t.get("proto") == "https"), None)
                        if https_tunnel:
                            return https_tunnel.get("public_url").rstrip("/")
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️  Could not detect public URL: {e}")
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
                    
                    # 2. Set Redirect URI for OAuth bridge
                    # We always want this so we can use direct installation links
                    # NOTE: Backend is on 8000, 3000 is Grafana.
                    base_url = (public_url or "http://localhost:8000").rstrip("/")
                    callback_url = f"{base_url}/api/v1/connections/auth/slack/agent/callback"
                    
                    if 'oauth_config' not in manifest_data:
                         manifest_data['oauth_config'] = {}
                    manifest_data['oauth_config']['redirect_urls'] = [callback_url]

                    # Choice B: HTTP Mode Configuration (if public URL is present)
                    if public_url:
                        # 1. Disable Socket Mode
                        if 'settings' not in manifest_data:
                            manifest_data['settings'] = {}
                        manifest_data['settings']['socket_mode_enabled'] = False
                        
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
                    except (KeyError, TypeError, json.JSONDecodeError) as e:
                        print(f"⚠️ Invalid stored Slack credentials for {agent_id}; falling back to create flow: {e}")
                        app_id = None
                        creds = {}

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
                            "app_id": app_id,
                            "transport": "http" if public_url else "socket",
                            "public_url": public_url
                        }),
                        username=manifest_data["display_information"]["name"]
                    )

                    # Construct Install URL
                    client_id = creds.get("client_id")
                    scopes = (
                        "app_mentions:read,chat:write,channels:history,groups:history,im:history,"
                        "reactions:write,channels:read,groups:read,im:read,channels:manage,groups:write,users:read"
                    )
                    
                    if client_id:
                        # Direct OAuth logic: more straightforward than sending to API dashboard
                        base_url = (public_url or "http://localhost:8000").rstrip("/")
                        redirect_uri = f"{base_url}/api/v1/connections/auth/slack/agent/callback"
                        install_url = (
                            f"https://slack.com/oauth/v2/authorize"
                            f"?client_id={client_id}"
                            f"&scope={scopes}"
                            f"&state={agent_id}"
                            f"&redirect_uri={redirect_uri}"
                        )
                    else:
                        # Fallback (shouldn't happen with Manifest API)
                        install_url = f"https://api.slack.com/apps/{app_id}"

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

    def sync_workspace_structure(self) -> Dict[str, Any]:
        """
        Synchronizes Slack channels and memberships based on the registry.
        Uses Alfredo's token as the primary administrative client.
        """
        # 1. Get Alfredo's token
        alfredo_token = user_connections_store.get_connection("slack_bot:alfredo")
        if not alfredo_token:
            return {"success": False, "error": "Alfredo is not connected. Please install Alfredo first."}
        
        client = WebClient(token=alfredo_token["access_token"])
        results = {"channels": [], "errors": []}
        
        # 2. Map Agent IDs to Bot User IDs (needed for invitations)
        agent_user_ids = {}
        for agent_id in ["alfredo", "vito", "riccardo", "rossini", "tommy", "bella", "kowalski", "giuseppina"]:
            bot_token_conn = user_connections_store.get_connection(f"slack_bot:{agent_id}")
            if bot_token_conn:
                try:
                    bot_client = WebClient(token=bot_token_conn["access_token"])
                    auth = bot_client.auth_test()
                    agent_user_ids[agent_id] = auth["user_id"]
                except Exception as e:
                    print(f"⚠️ Could not resolve bot user ID for {agent_id}: {e}")

        # 3. Process the Registry
        for code, config in self.registry.items():
            desired_name = config["name"]
            required_agents = config["agents"]
            
            # Check if we have a stored channel_id for this code
            stored_ref = user_connections_store.get_connection(f"slack_channel:{code}")
            channel_id = stored_ref["access_token"] if stored_ref else None
            
            # Verify channel in Slack
            slack_channel = None
            if channel_id:
                try:
                    info = client.conversations_info(channel=channel_id)
                    if info["ok"]:
                        slack_channel = info["channel"]
                except SlackApiError:
                    channel_id = None # Reset if not found
            
            # If not found by ID, try to find by name
            if not channel_id:
                try:
                    cursor = None
                    while True:
                        resp = client.conversations_list(types="public_channel,private_channel", cursor=cursor, limit=1000)
                        for chan in resp["channels"]:
                            if chan["name"] == desired_name:
                                channel_id = chan["id"]
                                slack_channel = chan
                                break
                        if channel_id or not resp.get("response_metadata", {}).get("next_cursor"):
                            break
                        cursor = resp["response_metadata"]["next_cursor"]
                except SlackApiError as e:
                    results["errors"].append(f"List channels failed: {e.response['error']}")

            # Create if still missing
            if not channel_id:
                try:
                    print(f"🔨 Creating channel: #{desired_name} ({code})")
                    resp = client.conversations_create(name=desired_name)
                    if resp["ok"]:
                        channel_id = resp["channel"]["id"]
                        user_connections_store.upsert_connection(
                            service=f"slack_channel:{code}",
                            access_token=channel_id,
                            username=desired_name
                        )
                except SlackApiError as e:
                    results["errors"].append(f"Failed to create #{desired_name}: {e.response['error']}")
                    continue
            else:
                # Rename if needed
                if slack_channel and slack_channel["name"] != desired_name:
                    try:
                        print(f"🔄 Renaming channel {slack_channel['name']} -> #{desired_name} ({code})")
                        client.conversations_rename(channel=channel_id, name=desired_name)
                        user_connections_store.upsert_connection(
                            service=f"slack_channel:{code}",
                            access_token=channel_id,
                            username=desired_name
                        )
                    except SlackApiError as e:
                        results["errors"].append(f"Failed to rename #{desired_name}: {e.response['error']}")

            # Join bots
            if channel_id:
                actual_agents_joined = []
                for agent_id in required_agents:
                    bot_user_id = agent_user_ids.get(agent_id)
                    if not bot_user_id:
                        continue
                        
                    try:
                        # Alfredo invites the bot
                        client.conversations_invite(channel=channel_id, users=bot_user_id)
                        actual_agents_joined.append(agent_id)
                    except SlackApiError as e:
                        # Often "already_in_channel" or "cant_invite_self", which we can ignore
                        if e.response["error"] not in ["already_in_channel", "cant_invite_self"]:
                            results["errors"].append(f"Invite {agent_id} to #{desired_name} failed: {e.response['error']}")
                        else:
                            actual_agents_joined.append(agent_id)
                
                results["channels"].append({
                    "code": code,
                    "name": desired_name,
                    "id": channel_id,
                    "agents": actual_agents_joined
                })

        return results

slack_provisioning = SlackProvisioningService()
