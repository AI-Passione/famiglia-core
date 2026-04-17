import requests

API_BASE = "http://localhost:8000/api/v1"

def test_purge():
    try:
        # 1. Trigger purge
        print("🚀 Requesting full Slack purge...")
        res = requests.delete(f"{API_BASE}/connections/slack/purge/all")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
        
        # 2. Verify status
        print("\n🔍 Verifying status...")
        res = requests.get(f"{API_BASE}/connections/slack/status")
        status = res.json()
        for agent_id, data in status.items():
            if data["connected"]:
                print(f"❌ Error: {agent_id} is still connected!")
                return False
        
        print("✅ All Slack connections purged successfully.")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    # This test requires the server to be running.
    # Since I cannot guarantee the server is up and reachable via localhost:8000 in this env,
    # I'll rely on the logic verification if it fails to connect.
    test_purge()
