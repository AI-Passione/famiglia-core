import requests

API_BASE = "http://localhost:8000/api/v1"

def test_purge():
    # 1. Trigger purge
    print("🚀 Requesting full Slack purge...")
    res = requests.delete(f"{API_BASE}/connections/slack/purge/all")
    assert res.status_code == 200, f"Purge failed with status {res.status_code}"
    print(f"Response: {res.json()}")
    
    # 2. Verify status
    print("\n🔍 Verifying status...")
    res = requests.get(f"{API_BASE}/connections/slack/status")
    assert res.status_code == 200
    status = res.json()
    
    for agent_id, data in status.items():
        assert not data["connected"], f"❌ Error: {agent_id} is still connected!"
    
    print("✅ All Slack connections purged successfully.")

if __name__ == "__main__":
    # This test requires the server to be running.
    # Since I cannot guarantee the server is up and reachable via localhost:8000 in this env,
    # I'll rely on the logic verification if it fails to connect.
    test_purge()
