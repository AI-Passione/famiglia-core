import os
import sys
from dotenv import load_dotenv

# Add src to path for direct script execution
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from famiglia_core.command_center.backend.comms.slack.provisioning import slack_provisioning

def push_manifests():
    load_dotenv()
    app_token = os.getenv("SLACK_APP_TOKEN") or os.getenv("SLACK_CONFIGURATION_TOKEN")
    
    if not app_token:
        print("❌ SLACK_APP_TOKEN not found in environment.")
        return

    try:
        print("🚀 Starting Smart Provisioning via SlackProvisioningService...")
        apps = slack_provisioning.provision_famiglia(app_level_token=app_token)
        
        print("\n✨ Provisioning Summary:")
        for app in apps:
            print(f"- {app['name']} (App ID: {app['app_id']})")
            print(f"  Install URL: {app['install_url']}")
        
        print("\n✅ All apps synced. 1:1 agent-bot enforcement complete.")

    except Exception as e:
        print(f"❌ Provisioning failed: {e}")

if __name__ == "__main__":
    push_manifests()
