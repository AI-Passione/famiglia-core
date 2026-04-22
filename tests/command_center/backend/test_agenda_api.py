import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from famiglia_core.command_center.backend.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_agenda_lifecycle(client, mocker):
    # Mock context_store methods in the agenda route
    # We use the path where it's imported in agenda.py
    mock_list = mocker.patch("famiglia_core.command_center.backend.api.routes.agenda.context_store.list_tasks_in_range")
    mock_create = mocker.patch("famiglia_core.command_center.backend.api.routes.agenda.context_store.create_scheduled_task")
    mock_update = mocker.patch("famiglia_core.command_center.backend.api.routes.agenda.context_store.update_task_instance")
    mock_cancel = mocker.patch("famiglia_core.command_center.backend.api.routes.agenda.context_store.cancel_scheduled_task")

    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1)
    end = start + timedelta(hours=2)
    
    # 1. Create an event
    mock_create.return_value = {
        "id": 123,
        "title": "Test Agenda Directive",
        "task_payload": "This is a test directive for the agenda",
        "eta_pickup_at": start.isoformat(),
        "eta_completion_at": end.isoformat(),
        "status": "queued",
        "priority": "high",
        "expected_agent": "alfredo",
        "metadata": {"test": True}
    }
    
    payload = {
        "title": "Test Agenda Directive",
        "description": "This is a test directive for the agenda",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "agent_id": "alfredo",
        "priority": "high",
        "metadata": {"test": True}
    }
    
    response = client.post("/api/v1/agenda/events", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["id"] == 123

    # 2. List events in range
    mock_list.return_value = [mock_create.return_value]
    
    range_start = start - timedelta(hours=1)
    range_end = end + timedelta(hours=1)
    
    import urllib.parse
    start_str = urllib.parse.quote(range_start.isoformat())
    end_str = urllib.parse.quote(range_end.isoformat())
    
    response = client.get(f"/api/v1/agenda/events?start={start_str}&end={end_str}")
    if response.status_code != 200:
        print(f"GET /events failed: {response.text}")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["id"] == 123

    # 3. Update the event
    mock_update.return_value = {**mock_create.return_value, "title": "Updated Title"}
    update_payload = {"title": "Updated Title"}
    response = client.patch("/api/v1/agenda/events/123", json=update_payload)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"

    # 4. Delete the event
    mock_cancel.return_value = True
    response = client.delete("/api/v1/agenda/events/123")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
