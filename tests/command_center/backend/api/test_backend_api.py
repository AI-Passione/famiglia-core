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
            "timestamp": datetime.now(timezone.utc),
            "agent_name": "alfredo",
            "action_type": "web_search",
            "action_details": {"query": "test"},
            "approval_status": "approved",
            "cost_usd": 0.0,
            "duration_seconds": 2,
            "completed_at": datetime.now(timezone.utc)
        }
    ]
    mock_store.get_total_agent_action_count.return_value = 1
    
    response = client.get("/api/v1/actions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["actions"]) == 1
    assert data["total"] == 1

@patch("famiglia_core.command_center.backend.api.main.context_store")
def test_get_conversations_endpoint(mock_store):
    mock_store.list_conversations.return_value = [
        {
            "id": 1,
            "conversation_key": "test_conv",
            "metadata": {},
            "updated_at": datetime.now(timezone.utc),
            "latest_message": "hello",
            "latest_agent": "alfredo"
        }
    ]
    mock_store.get_total_conversation_count.return_value = 1
    
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) == 1
    assert data["total"] == 1
    assert data["conversations"][0]["conversation_key"] == "test_conv"

@patch("famiglia_core.command_center.backend.api.main.context_store")
def test_get_recurring_tasks_endpoint(mock_store):
    mock_store.list_recurring_tasks.return_value = [
        {
            "id": 7,
            "title": "Weekly strategy sync",
            "task_payload": "Prepare the Monday priority brief.",
            "priority": "high",
            "expected_agent": "alfredo",
            "metadata": {"category": "strategy"},
            "schedule_config": {"days": [0], "hour": 9, "minute": 30},
            "last_spawned_at": datetime(2026, 3, 30, 9, 30, 0, tzinfo=timezone.utc),
            "created_at": datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 3, 30, 9, 31, 0, tzinfo=timezone.utc),
        }
    ]

    response = client.get("/api/v1/recurring-tasks")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["title"] == "Weekly strategy sync"
    assert payload[0]["schedule_config"]["hour"] == 9

@patch("famiglia_core.command_center.backend.api.routes.settings.user_service")
def test_get_settings_endpoint(mock_user_service):
    mock_user_service.get_don_settings.return_value = {
        "honorific": "Capo",
        "famigliaName": "The Family",
        "notificationsEnabled": False,
        "backgroundAnimationsEnabled": True,
        "personalDirective": "Be efficient.",
        "systemPrompt": "Shared baseline content",
    }

    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    assert response.json()["honorific"] == "Capo"
    assert response.json()["notificationsEnabled"] is False
    assert response.json()["personalDirective"] == "Be efficient."


@patch("famiglia_core.command_center.backend.api.routes.settings.user_service")
def test_update_settings_endpoint(mock_user_service):
    payload = {
        "honorific": "Donna",
        "famigliaName": "The Family",
        "notificationsEnabled": True,
        "backgroundAnimationsEnabled": False,
    }
    expected_payload = {
        **payload,
        "personalDirective": "",
        "systemPrompt": "",
    }
    mock_user_service.update_don_settings.return_value = expected_payload

    response = client.put("/api/v1/settings", json=payload)
    assert response.status_code == 200
    assert response.json() == expected_payload
    mock_user_service.update_don_settings.assert_called_once_with(expected_payload)


@patch("famiglia_core.command_center.backend.api.routes.famiglia.context_store")
def test_get_famiglia_agents_endpoint(mock_store):
    mock_store.list_famiglia_agents.return_value = [
        {
            "id": "alfredo",
            "agent_id": "alfredo",
            "name": "Alfredo",
            "role": "Strategic Lead",
            "status": "active",
            "aliases": ["Chief of Staff"],
            "personality": "Calm and precise",
            "identity": "Coordinates the family.",
            "skills": ["Coordination"],
            "tools": ["openclaw-api"],
            "workflows": ["Command Center"],
            "latest_conversation_snippet": "Status confirmed.",
            "last_active": datetime(2026, 3, 31, 17, 0, 0, tzinfo=timezone.utc),
        }
    ]

    response = client.get("/api/v1/famiglia/agents")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Alfredo"
    assert payload[0]["skills"] == ["Coordination"]
    assert payload[0]["agent_id"] == "alfredo"


@patch("famiglia_core.command_center.backend.api.main.engine_room_service")
def test_get_engine_room_snapshot(mock_engine_room_service):
    mock_engine_room_service.get_snapshot.return_value = {
        "scope": "local-only",
        "generated_at": "2026-04-01T11:30:00+00:00",
        "host": {
            "hostname": "la-passione.local",
            "platform": {
                "system": "Darwin",
                "release": "24.0.0",
                "machine": "arm64",
                "python": "3.12.8",
            },
            "uptime": {"seconds": 3600, "display": "1h", "source": "uptime_command"},
            "cpu": {
                "cores": 10,
                "load_average": [1.2, 1.4, 1.6],
                "estimated_load_percent": 12.0,
                "source": "load_average_per_core",
            },
            "memory": {
                "total_bytes": 100,
                "used_bytes": 50,
                "available_bytes": 50,
                "usage_percent": 50.0,
                "source": "vm_stat",
            },
            "disk": {
                "path": "/tmp",
                "total_bytes": 100,
                "used_bytes": 50,
                "free_bytes": 50,
                "usage_percent": 50.0,
            },
        },
        "tools": {"summary": {"total": 1, "ready": 1, "connected": 1, "configured": 1}, "items": []},
        "docker": {
            "available": True,
            "compose_file": "/tmp/docker-compose.yml",
            "diagnostics": [],
            "summary": {"declared": 1, "reachable": 1, "live": 1, "healthy": 1},
            "services": [],
        },
        "observability": {
            "summary": {"total": 1, "configured": 1, "reachable": 1},
            "metrics": [],
            "items": [],
        },
    }

    response = client.get("/api/v1/engine-room")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "local-only"
    assert payload["docker"]["summary"]["healthy"] == 1
    mock_engine_room_service.get_snapshot.assert_called_once()
