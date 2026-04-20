import os
import yaml
import json
import requests
from datetime import datetime, timezone
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
            "COMMAND_CENTER": {
                "name": "command-center",
                "primary": "alfredo",
                "agents": ["alfredo", "vito", "riccardo", "rossini", "tommy", "bella", "kowalski", "giuseppina"]
            },
            "TECH": {"name": "tech", "primary": "riccardo", "agents": ["riccardo"]},
            "ANALYTICS": {"name": "analytics", "primary": "kowalski", "agents": ["kowalski"]},
            "OPERATIONS": {"name": "operations", "primary": "tommy", "agents": ["tommy"]},
            "ALERTS": {"name": "alerts", "primary": "riccardo", "agents": ["riccardo"]},
            "INCIDENTS": {"name": "incidents", "primary": "riccardo", "agents": ["riccardo"]},
            "FINANCE": {"name": "finance", "primary": "vito", "agents": ["vito"]},
            "ADMIN": {"name": "admin", "primary": "bella", "agents": ["bella"]},
            "PROJECTS": {"name": "projects", "primary": "rossini", "agents": ["riccardo", "rossini"]},
            "RESEARCH_INSIGHTS": {"name": "research-insights", "primary": "rossini", "agents": ["rossini"]},
            "PRODUCT_STRATEGY": {"name": "product", "primary": "rossini", "agents": ["rossini"]},
            "CORE_FAMIGLIA": {
                "name": "the-famiglia",
                "primary": "giuseppina",
                "agents": ["alfredo", "vito", "riccardo", "rossini", "tommy", "bella", "kowalski", "giuseppina"]
            }
        }

    def _seed_agent_greetings(self):
        """Seed daily greeting tasks for each primary agent in their channel."""
        print("🌱 Seeding daily agent greetings...")
        from famiglia_core.db.agents.context_store import context_store
        from famiglia_core.agents.orchestration.utils.task_helpers import TASK_TYPE_AGENT_GREETING

        for code, config in self.registry.items():
            primary_agent = config.get("primary")
            if not primary_agent:
                continue
            
            # Fetch the actual channel ID from storage
            stored_ref = user_connections_store.get_connection(f"slack_channel:{code}")
            if not stored_ref:
                continue
            channel_id = stored_ref["access_token"]
            
            title = f"Initial Greeting: {primary_agent.capitalize()} in #{config['name']}"
            
            # For 1-off tasks, we check task_instances to see if it was ever queued/run
            # This prevents spamming greetings every time the sync button is clicked.
            existing_tasks = context_store.list_scheduled_tasks(limit=100)
            if not any(t["title"] == title for t in existing_tasks):
                print(f"  + Scheduling 1-off greeting: {title} for {channel_id}")
                context_store.create_scheduled_task(
                    title=title,
                    task_payload=f"You are the primary agent for #{config['name']}. Introduce yourself to the channel and mention your core focus. Finish with 'The Famiglia is operational.'",
                    priority="low",
                    expected_agent=primary_agent,
                    created_by_name="SlackProvisioningService",
                    metadata={
                        "task_type": TASK_TYPE_AGENT_GREETING,
                        "channel_id": channel_id,
                        "channel_name": config["name"]
                    }
                )
            else:
                print(f"  - Skipping greeting (already exists): {title}")

    def _get_public_url(self) -> Optional[str]:
        """Fetch the public URL from environment or ngrok container's API."""
        # 1. Check direct environment overrides first (including NGROK_DOMAIN)
        env_url = (
            os.getenv("PUBLIC_URL") or 
            os.getenv("SLACK_REDIRECT_HOST") or
            os.getenv("NGROK_DOMAIN")
        )
        if env_url:
            # If NGROK_DOMAIN is just 'foo.ngrok-free.app', prefix it
            if "://" not in env_url:
                env_url = f"https://{env_url}"
            return env_url.rstrip("/")

        # 2. Try to detect from ngrok's local API
        try:
            # We use 'ngrok' as the hostname since it's the service name in docker-compose
            for host in ["ngrok", "localhost"]:
                try:
                    response = requests.get(f"http://{host}:4040/api/tunnels", timeout=1)
                    if response.ok:
                        tunnels = response.json().get("tunnels", [])
                        # Prioritize https, then http
                        for proto in ["https", "http"]:
                            tunnel = next((t for t in tunnels if t.get("proto") == proto), None)
                            if tunnel:
                                return tunnel.get("public_url").rstrip("/")
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️  Could not detect public URL: {e}")
        return None

    def cleanup_orphaned_apps(self, client: WebClient) -> Dict[str, Any]:
        """
        Deletes Slack apps that are tracked in our database but no longer in the agent registry.
        """
        print("🧹 Scanning for orphaned Slack apps...")
        results = {"deleted": [], "errors": []}
        
        # Get all agents currently defined in the registry
        active_agents = set()
        for config in self.registry.values():
            active_agents.update(config.get("agents", []))
        
        # Find all stored credentials
        all_creds = user_connections_store.list_connections("slack_creds:")
        for service, conn in all_creds.items():
            agent_id = service.replace("slack_creds:", "")
            if agent_id not in active_agents:
                try:
                    data = json.loads(conn["access_token"])
                    app_id = data.get("app_id")
                    if app_id:
                        print(f"📦 Deleting orphaned bot: {agent_id} (App ID: {app_id})")
                        client.apps_manifest_delete(app_id=app_id)
                        user_connections_store.delete_connection(service)
                        # Also delete bot and socket connections if they exist
                        user_connections_store.delete_connection(f"slack_bot:{agent_id}")
                        user_connections_store.delete_connection(f"slack_socket:{agent_id}")
                        results["deleted"].append({"agent_id": agent_id, "app_id": app_id})
                except Exception as e:
                    print(f"⚠️ Failed to delete orphaned bot {agent_id}: {e}")
                    results["errors"].append(f"Failed to delete {agent_id}: {str(e)}")
        
        return results

    def _rotate_bootstrap_token(self, refresh_token: str) -> Optional[str]:
        """Rotates the Slack App Configuration Token using the tooling.tokens.rotate API."""
        print("🔄 Rotating Slack App Configuration Token...")
        try:
            response = requests.post(
                "https://slack.com/api/tooling.tokens.rotate",
                data={"refresh_token": refresh_token},
                timeout=10
            )
            data = response.json()
            if data.get("ok"):
                new_token = data.get("token")
                new_refresh = data.get("refresh_token")
                user_connections_store.upsert_connection(
                    service="slack_bootstrap",
                    access_token=new_token,
                    refresh_token=new_refresh,
                    username="Bootstrapper"
                )
                print("✅ Token rotated successfully.")
                return new_token
            else:
                print(f"❌ Token rotation failed: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error during token rotation: {e}")
        return None

    def provision_famiglia(self, app_level_token: str = None) -> List[Dict[str, Any]]:
        """
        Create or update Slack apps for the entire Famiglia roster.
        """
        if not app_level_token:
            conn = user_connections_store.get_connection("slack_bootstrap")
            if conn:
                app_level_token = conn["access_token"]
                refresh_token = conn.get("refresh_token")
                updated_at_str = conn.get("updated_at")
                
                # Auto-Rotation Check: If token is > 10 hours old and we have a refresh token, rotate it.
                if refresh_token and updated_at_str:
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str)
                        if (datetime.now(timezone.utc) - updated_at).total_seconds() > 36000: # 10 hours
                             rotated_token = self._rotate_bootstrap_token(refresh_token)
                             if rotated_token:
                                 app_level_token = rotated_token
                    except Exception as e:
                        print(f"⚠️ Failed to auto-check token rotation: {e}")
        
        if not app_level_token:
            raise ValueError("No Slack App Configuration Token found. Please provide one in the setup.")

        client = WebClient(token=app_level_token)
        
        # 1. Cleanup Phase: Delete apps owned by the system that are no longer in registry
        self.cleanup_orphaned_apps(client)

        manifest_dir = os.path.join(os.path.dirname(__file__), "app_manifest")
        manifest_files = [os.path.join(manifest_dir, f) for f in os.listdir(manifest_dir) if f.endswith(".yaml") or f.endswith(".yml")]
        
        provisioned_apps = []

        # Detect public URL for Choice B (Total Automation)
        public_url = self._get_public_url()
        if public_url:
            print(f"🌐 Detected Public Tunnel: {public_url}")
        else:
            print("💡 No public tunnel detected. Falling back to Socket Mode (Semi-Automated).")

        for manifest_path in manifest_files:
            filename = os.path.basename(manifest_path)
            if filename == "passione_famiglia.yaml":
                continue
                
            agent_id = filename.replace(".yaml", "").replace(".yml", "")
            
            with open(manifest_path, 'r') as f:
                try:
                    manifest_data = yaml.safe_load(f)
                    base_url = (public_url or "http://localhost:8000").rstrip("/")
                    callback_url = f"{base_url}/api/v1/connections/auth/slack/agent/callback"
                    
                    if 'oauth_config' not in manifest_data:
                         manifest_data['oauth_config'] = {}
                    manifest_data['oauth_config']['redirect_urls'] = [callback_url]

                    if public_url:
                        if 'settings' not in manifest_data:
                            manifest_data['settings'] = {}
                        manifest_data['settings']['socket_mode_enabled'] = False
                        
                        events_url = f"{public_url}/api/v1/connections/slack/events/{agent_id}"
                        if 'event_subscriptions' not in manifest_data['settings']:
                            manifest_data['settings']['event_subscriptions'] = {}
                        manifest_data['settings']['event_subscriptions']['request_url'] = events_url
                        
                        if 'interactivity' not in manifest_data['settings']:
                             manifest_data['settings']['interactivity'] = {}
                        manifest_data['settings']['interactivity']['request_url'] = events_url

                    if 'settings' in manifest_data:
                        manifest_data['settings'].pop('is_mcp_enabled', None)

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

                response = None
                if app_id:
                    print(f"🔄 Syncing existing {agent_id} (App ID: {app_id})...")
                    try:
                        response = client.apps_manifest_update(app_id=app_id, manifest=manifest_str)
                    except SlackApiError as e:
                        error_code = e.response['error']
                        # If the app is missing or Slack returns an internal error (usually due to stale IDs),
                        # we purge the local reference and fall back to the creation flow.
                        if error_code in ["app_not_found", "internal_error", "access_denied"]:
                            print(f"⚠️ App {app_id} is stale or inaccessible ({error_code}). Purging and re-creating...")
                            user_connections_store.delete_connection(f"slack_creds:{agent_id}")
                            app_id = None
                        else:
                            raise e

                if not app_id:
                    print(f"📦 Manifesting new {agent_id}...")
                    response = client.apps_manifest_create(manifest=manifest_str)
                
                if response and response["ok"]:
                    if not app_id:
                        app_id = response["app_id"]
                        creds = response.get("credentials", {})
                    
                    user_connections_store.upsert_connection(
                        service=f"slack_creds:{agent_id}",
                        access_token=json.dumps({
                            "client_id": creds.get("client_id"),
                            "client_secret": creds.get("client_secret"),
                            "app_id": app_id,
                            "transport": "http" if public_url else "socket",
                            "public_url": public_url
                        }),
                        username=manifest_data["display_information"]["name"],
                        app_id=app_id
                    )

                    client_id = creds.get("client_id")
                    scopes = (
                        "app_mentions:read,chat:write,channels:history,groups:history,im:history,"
                        "reactions:write,channels:read,groups:read,im:read,channels:manage,channels:join,groups:write,users:read"
                    )
                    
                    if client_id:
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
                        install_url = f"https://api.slack.com/apps/{app_id}"

                    app_info = {
                        "agent_id": agent_id,
                        "name": manifest_data["display_information"]["name"],
                        "app_id": app_id,
                        "install_url": install_url
                    }
                    provisioned_apps.append(app_info)
                    status_icon = "✅ Updated" if existing_creds and app_id else "✅ Created"
                    print(f"{status_icon} {agent_id} (App ID: {app_id})")
                else:
                    err = response["error"] if response else "Unknown Error"
                    print(f"❌ Failed to process {agent_id}: {err}")
            except SlackApiError as e:
                error_code = e.response['error']
                print(f"❌ Slack API Error for {agent_id}: {error_code}")
                
                # If token expired during the loop, try ONE rotation and retry this agent
                if error_code == "token_expired":
                    conn = user_connections_store.get_connection("slack_bootstrap")
                    if conn and conn.get("refresh_token"):
                        new_token = self._rotate_bootstrap_token(conn["refresh_token"])
                        if new_token:
                            print(f"🔄 Retrying {agent_id} with new token...")
                            client = WebClient(token=new_token)
                            # Simple one-time retry
                            try:
                                if app_id:
                                    client.apps_manifest_update(app_id=app_id, manifest=manifest_str)
                                else:
                                    client.apps_manifest_create(manifest=manifest_str)
                                print(f"✅ Retry successful for {agent_id}")
                            except Exception as re:
                                print(f"❌ Retry failed for {agent_id}: {re}")
            except Exception as e:
                print(f"❌ Unexpected error manifesting {agent_id}: {e}")

                
        return provisioned_apps

    def finalize_agent(self, agent_id: str, bot_token: str, app_token: str, app_id: str = None) -> bool:
        """
        Stores the final tokens for an agent and activates the connection.
        """
        # Resolve app_id from creds if not passed explicitly
        if not app_id:
            creds_conn = user_connections_store.get_connection(f"slack_creds:{agent_id}")
            if creds_conn:
                try:
                    # Prioritize new app_id column, fallback to JSON parsing
                    app_id = creds_conn.get("app_id")
                    if not app_id:
                        data = json.loads(creds_conn["access_token"])
                        app_id = data.get("app_id")
                except Exception:
                    pass

        # Store Bot Token
        bot_success = user_connections_store.upsert_connection(
            service=f"slack_bot:{agent_id}",
            access_token=bot_token,
            app_id=app_id,
            username="system"
        )
        
        # Store App/Socket Token
        app_success = user_connections_store.upsert_connection(
            service=f"slack_socket:{agent_id}",
            access_token=app_token,
            app_id=app_id,
            username="system"
        )
        
        return bot_success and app_success

    def _sync_registry_to_db(self):
        """
        Synchronizes the hardcoded registry to PostgreSQL as a baseline.
        This allows other parts of the system (like routing) to be dynamic.
        """
        print("💾 Synchronizing Slack Registry to PostgreSQL...")
        from famiglia_core.db.agents.context_store import context_store
        
        # Store the current registry as the authoritative 'baseline'
        # We store it in agent_memories under agent_name='system'
        context_store.upsert_memory(
            agent_name="system",
            memory_key="slack_agent_registry",
            memory_value=json.dumps(self.registry),
            metadata={"type": "slack_configuration", "updated_at": datetime.now(timezone.utc).isoformat()}
        )
        
        # Also store a flat routing map for faster lookups in task_helpers
        # We infer routing from the 'primary' agent assignments and common patterns
        # But for now, we'll just store the registry and let task_helpers use the hardcoded mapping
        # unless we specifically want to override it in DB.

    def sync_workspace_structure(self) -> Dict[str, Any]:
        """
        Synchronizes Slack channels and memberships based on the registry.
        Uses Alfredo's token as the primary administrative client.
        """
        # 0. Baseline Sync
        self._sync_registry_to_db()

        # 1. Get Alfredo's token
        alfredo_token_conn = user_connections_store.get_connection("slack_bot:alfredo")
        if not alfredo_token_conn:
            return {"success": False, "error": "Alfredo is not connected. Please install Alfredo first."}
        
        alfredo_token = alfredo_token_conn["access_token"]
        client = WebClient(token=alfredo_token)
        try:
            auth = client.auth_test()
            print(f"📡 Syncing with Slack Workspace: {auth.get('team')} ({auth.get('url')})")
        except Exception as e:
            print(f"❌ Slack Auth Test failed: {e}")
            return {"success": False, "error": f"Slack Auth Test failed: {e}"}

        # --- OWNER DISCOVERY ---
        owner_id = None
        owner_conn = user_connections_store.get_connection("slack_owner")
        if owner_conn:
            owner_id = owner_conn["access_token"]
        
        # Fallback 1: Programmatic Discovery via Primary Owner
        if not owner_id:
            try:
                print("🔍 Programmatically identifying workspace owner...")
                users_resp = client.users_list()
                if users_resp["ok"]:
                    for member in users_resp["members"]:
                        if member.get("is_primary_owner"):
                            owner_id = member["id"]
                            print(f"👑 Found Primary Owner: {member.get('real_name')} ({owner_id})")
                            # Cache it
                            user_connections_store.upsert_connection(service="slack_owner", access_token=owner_id)
                            break
            except Exception as e:
                print(f"⚠️ Programmatic owner discovery failed: {e}")

        # Fallback 2: Environment Variable
        if not owner_id:
            owner_id = os.getenv("USER_SLACK_ID")
            if owner_id:
                print(f"🏠 Fallback to environment USER_SLACK_ID: {owner_id}")

        results = {"channels": [], "archived": [], "errors": []}
        
        # --- CLEANUP PHASE ---
        try:
            print("🧹 Scanning for deprecated channels to archive...")
            all_connections = user_connections_store.list_connections("slack_channel:")
            for service, conn in all_connections.items():
                code = service.replace("slack_channel:", "")
                if code not in self.registry:
                    channel_id = conn["access_token"]
                    channel_name = conn.get("username", "unknown")
                    try:
                        print(f"📦 Archiving deprecated channel: #{channel_name} ({code})")
                        client.conversations_archive(channel=channel_id)
                        user_connections_store.delete_connection(service)
                        results["archived"].append({"code": code, "name": channel_name, "id": channel_id})
                    except SlackApiError as e:
                        if e.response["error"] == "already_archived":
                            user_connections_store.delete_connection(service)
                        else:
                            print(f"⚠️ Failed to archive #{channel_name}: {e.response['error']}")
                            results["errors"].append(f"Failed to archive #{channel_name}: {e.response['error']}")
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

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
                        print(f"✅ Created channel ID: {channel_id}")
                        user_connections_store.upsert_connection(
                            service=f"slack_channel:{code}",
                            access_token=channel_id,
                            username=desired_name
                        )
                except SlackApiError as e:
                    error_msg = e.response['error']
                    print(f"❌ Failed to create #{desired_name}: {error_msg}")
                    results["errors"].append(f"Failed to create #{desired_name}: {error_msg}")
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

            # Persist resolved ID if it wasn't already in DB
            if channel_id and not stored_ref:
                user_connections_store.upsert_connection(
                    service=f"slack_channel:{code}",
                    access_token=channel_id,
                    username=desired_name
                )

            # Join bots & owner
            if channel_id:
                actual_agents_joined = []
                
                # IMPORTANT: Alfredo MUST join the channel first to invite others
                try:
                    client.conversations_join(channel=channel_id)
                except SlackApiError as e:
                    join_error = e.response["error"]
                    if join_error != "already_in_channel":
                        print(f"⚠️ Alfredo failed to join #{desired_name}: {join_error}")

                # Invite Owner first
                if owner_id:
                    try:
                        client.conversations_invite(channel=channel_id, users=owner_id)
                    except SlackApiError as e:
                        if e.response["error"] not in ["already_in_channel", "cant_invite_self"]:
                            print(f"⚠️ Failed to invite owner {owner_id} to #{desired_name}: {e.response['error']}")

                for agent_id in required_agents:
                    bot_user_id = agent_user_ids.get(agent_id)
                    if not bot_user_id:
                        continue
                        
                    try:
                        # Alfredo invites the bot
                        client.conversations_invite(channel=channel_id, users=bot_user_id)
                        actual_agents_joined.append(agent_id)
                        print(f"  + Invited {agent_id} to #{desired_name}")
                    except SlackApiError as e:
                        invite_err = e.response["error"]
                        # Often "already_in_channel" or "cant_invite_self", which we can ignore
                        if invite_err in ["already_in_channel", "cant_invite_self"]:
                            actual_agents_joined.append(agent_id)
                        else:
                            print(f"⚠️ Failed to invite {agent_id} to #{desired_name}: {invite_err}")
                            results["errors"].append(f"Invite {agent_id} to #{desired_name} failed: {invite_err}")
                
                results["channels"].append({
                    "code": code,
                    "name": desired_name,
                    "id": channel_id,
                    "agents": actual_agents_joined
                })

        # 5. Seed greetings if needed
        self._seed_agent_greetings()
        
        return results

slack_provisioning = SlackProvisioningService()
