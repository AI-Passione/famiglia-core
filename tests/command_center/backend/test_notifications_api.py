import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime, timezone
import json

from famiglia_core.command_center.backend.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_global_notifications_merged(client, mocker):
    # Mock context_store
    mock_store = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.context_store")
    
    # 1. Setup mock app notifications
    now = datetime.now(timezone.utc)
    mock_store.get_app_notifications.return_value = [
        {
            "id": 1,
            "source": "workflow",
            "agent_name": "rossini",
            "title": "System Update",
            "message": "Market analysis ready.",
            "type": "success",
            "task_id": 101,
            "metadata": {"prio": 1},
            "created_at": now
        }
    ]
    
    # 2. Setup mock agent messages (Legacy Dual-Stream)
    mock_store.get_global_recent_agent_messages.return_value = [
        {
            "id": 500,
            "sender": "Alfredo",
            "content": "Mission started.",
            "metadata": json.dumps({"type": "mission_dispatch", "task_id": 102}),
            "created_at": now
        }
    ]
    
    response = client.get("/api/v1/chat/notifications", params={"limit": 5})
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    
    # Check for prefix IDs
    ids = [item["id"] for item in data]
    assert "app-1" in ids
    assert "msg-500" in ids
    
    # Check metadata parsing
    notif_msg = next(item for item in data if item["id"] == "msg-500")
    assert notif_msg["task_id"] == 102
    assert notif_msg["title"] == "Mission Dispatched"

def test_mark_notification_read_endpoint(client, mocker):
    mock_store = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.context_store")
    mock_store.mark_app_notification_as_read.return_value = True
    
    response = client.post("/api/v1/chat/notifications/123/read")
    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_store.mark_app_notification_as_read.assert_called_once_with(123)

def test_mark_notification_read_not_found(client, mocker):
    mock_store = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.context_store")
    mock_store.mark_app_notification_as_read.return_value = False
    
    response = client.post("/api/v1/chat/notifications/999/read")
    assert response.status_code == 404
