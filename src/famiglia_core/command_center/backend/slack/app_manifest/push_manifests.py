import os
import yaml
import glob
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def push_manifests():
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        print("❌ SLACK_APP_TOKEN not found in environment. Please set it in .env or env.local.")
        return

    client = WebClient(token=app_token)
    
    # Find all yaml files in the same directory as this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_files = glob.glob(os.path.join(current_dir, "*.yaml"))

    for manifest_path in manifest_files:
        filename = os.path.basename(manifest_path)
        if filename == "passione_famiglia.yaml":
            continue

        print(f"📦 Processing {filename}...")
        
        with open(manifest_path, 'r') as f:
            try:
                manifest_data = yaml.safe_load(f)
                # Convert dict to string for Slack API
                manifest_str = yaml.dump(manifest_data)
            except yaml.YAMLError as e:
                print(f"❌ Error parsing {filename}: {e}")
                continue

        try:
            # Note: apps.manifest.create requires an App-level token (xapp-...)
            # and the app that owns the token must have apps.manifest:write scope
            response = client.apps_manifest_create(manifest=manifest_str)
            
            if response["ok"]:
                app_id = response["app_id"]
                creds = response["credentials"]
                print(f"✅ Created Slack App: {manifest_data['display_information']['name']}")
                print(f"   App ID: {app_id}")
                print(f"   Client ID: {creds['client_id']}")
                print(f"   Client Secret: {creds['client_secret']}")
                print(f"   Signing Secret: {creds['signing_secret']}")
                print("-" * 40)
            else:
                print(f"❌ Failed to create app {filename}: {response['error']}")

        except SlackApiError as e:
            if e.response["error"] == "invalid_manifest":
                print(f"❌ Invalid manifest in {filename}: {e.response['errors']}")
            else:
                print(f"❌ Slack API Error: {e.response['error']}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    push_manifests()
