import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

@patch("famiglia_core.command_center.backend.api.main.context_store")
def test_get_agents_endpoint(mock_store):
    # Mocking agent interaction stats
    mock_store.get_agent_interaction_stats.return_value = {
        "alfredo": {"msg_count": 10, "last_active": datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)},
        "vito": {"msg_count": 5, "last_active": datetime(2026, 3, 31, 14, 0, 0, tzinfo=timezone.utc)}
    }
    
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7  # 7 agents in list
    alfredo = next(a for a in data if a["name"] == "alfredo")
    assert alfredo["msg_count"] == 10

@patch("famiglia_core.command_center.backend.api.main.context_store")
def test_get_actions_endpoint(mock_store):
    mock_store.list_agent_actions.return_value = [
        {
            "id": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": "alfredo",
            "action_type": "web_search",
            "action_details": {"query": "test"},
            "approval_status": "approved",
            "cost_usd": 0.0,
            "duration_seconds": 2,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    response = client.get("/api/v1/actions")
    assert response.status_code == 200
    assert len(response.json()) == 1

@patch("famiglia_core.command_center.backend.api.main.graph_parser")
def test_get_graphs_endpoint(mock_parser):
    mock_parser.parse_all_graphs.return_value = [
        {
            "id": "test_graph", 
            "name": "Test Graph", 
            "nodes": [{"id": "START", "label": "Start", "type": "entry"}, {"id": "END", "label": "End", "type": "end"}],
            "edges": [{"source": "START", "target": "END"}]
        }
    ]
    
    response = client.get("/api/v1/graphs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test_graph"
    assert len(data[0]["nodes"]) == 2

@patch("famiglia_core.command_center.backend.api.main.context_store")
def test_get_mission_logs_endpoint(mock_store):
    # Mocking DB connection and cursor for mission logs
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_store._get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        {
            "id": 101,
            "created_at": datetime(2026, 3, 31, 15, 0, 0),
            "status": "completed",
            "picked_up_at": datetime(2026, 3, 31, 15, 0, 1),
            "completed_at": datetime(2026, 3, 31, 15, 0, 5),
            "initiator": "Don Jimmy"
        }
    ]
    
    response = client.get("/api/v1/mission-logs/test_graph")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "ML-101"
    assert data[0]["status"] == "success"

@patch("famiglia_core.command_center.backend.api.routes.settings.user_service")
def test_get_settings_endpoint(mock_user_service):
    mock_user_service.get_don_settings.return_value = {
        "honorific": "Capo",
        "notificationsEnabled": False,
        "backgroundAnimationsEnabled": True,
    }

    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    assert response.json()["honorific"] == "Capo"
    assert response.json()["notificationsEnabled"] is False


@patch("famiglia_core.command_center.backend.api.routes.settings.user_service")
def test_update_settings_endpoint(mock_user_service):
    payload = {
        "honorific": "Donna",
        "notificationsEnabled": True,
        "backgroundAnimationsEnabled": False,
    }
    mock_user_service.update_don_settings.return_value = payload

    response = client.put("/api/v1/settings", json=payload)
    assert response.status_code == 200
    assert response.json() == payload
    mock_user_service.update_don_settings.assert_called_once_with(payload)
