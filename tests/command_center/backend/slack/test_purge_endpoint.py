from unittest.mock import patch
from fastapi.testclient import TestClient
from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

CONNECTIONS_STORE = "famiglia_core.command_center.backend.api.routes.connections.user_connections_store"

@patch(CONNECTIONS_STORE)
def test_purge(mock_store):
    # 1. Mock successful purge
    mock_store.delete_connections_by_prefix.return_value = True
    
    # 2. Mock status check (all disconnected)
    mock_store.get_connection_status.return_value = {"connected": False}
    
    # 3. Trigger purge via TestClient
    print("🚀 Requesting full Slack purge...")
    response = client.delete("/api/v1/connections/slack/purge/all")
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # 4. Verify status
    print("\n🔍 Verifying status...")
    status_response = client.get("/api/v1/connections/slack/status")
    assert status_response.status_code == 200
    status = status_response.json()
    
    for agent_id, data in status.items():
        assert not data["connected"], f"❌ Error: {agent_id} is still connected!"
    
    print("✅ All Slack connections purged successfully.")
