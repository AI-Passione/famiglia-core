from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

@patch("famiglia_core.command_center.backend.api.routes.operations.graph_parser")
def test_get_graphs_endpoint(mock_parser):
    mock_parser.parse_all_graphs.return_value = [
        {
            "id": "prd_drafting", 
            "name": "PRD Drafting", 
            "nodes": [{"id": "START", "label": "Start", "type": "entry"}, {"id": "END", "label": "End", "type": "end"}],
            "edges": [{"source": "START", "target": "END"}]
        }
    ]
    
    response = client.get("/api/v1/operations/graphs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "prd_drafting"

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
def test_get_mission_logs_endpoint(mock_store):
    # Mocking DB session for mission logs
    mock_cursor = MagicMock()
    mock_store.db_session.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        {
            "id": 101,
            "created_at": datetime(2026, 3, 31, 15, 0, 0, tzinfo=timezone.utc),
            "status": "completed",
            "picked_up_at": datetime(2026, 3, 31, 15, 0, 1, tzinfo=timezone.utc),
            "completed_at": datetime(2026, 3, 31, 15, 0, 5, tzinfo=timezone.utc),
            "initiator": "Don"
        }
    ]
    
    response = client.get("/api/v1/operations/mission-logs/prd_drafting")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "ML-101"
    assert data[0]["status"] == "success"

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
def test_get_all_mission_logs_endpoint(mock_store):
    # Mocking DB session for global mission logs
    mock_cursor = MagicMock()
    mock_store.db_session.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        {
            "id": 202,
            "graph_id": "prd_drafting",
            "created_at": datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc),
            "status": "in_progress",
            "picked_up_at": datetime(2026, 4, 1, 10, 0, 1, tzinfo=timezone.utc),
            "completed_at": None,
            "initiator": "Don"
        }
    ]
    
    response = client.get("/api/v1/operations/mission-logs/all")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "ML-202"
    assert data[0]["graph_id"] == "prd_drafting"
    assert data[0]["status"] == "running"

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
@patch("famiglia_core.command_center.backend.api.routes.operations.os.walk")
@patch("famiglia_core.command_center.backend.api.routes.operations.graph_parser")
def test_execute_graph_endpoint(mock_parser, mock_walk, mock_store):
    # Mock finding the graph file
    mock_walk.return_value = [
        ("/path/to/features/product_development", [], ["prd_drafting.py"])
    ]
    mock_parser.parse_file.return_value = MagicMock(id="prd_drafting", name="PRD Drafting")
    
    # Mock task creation
    mock_store.create_scheduled_task.return_value = {
        "id": 999,
        "title": "Execute Operations: PRD Drafting"
    }
    
    response = client.post("/api/v1/operations/graphs/prd_drafting/execute")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 999
    assert "ML-999" in data["message"]
    
    mock_store.create_scheduled_task.assert_called_once()
    args, kwargs = mock_store.create_scheduled_task.call_args
    assert kwargs["metadata"]["graph_id"] == "prd_drafting"

def test_execute_graph_not_found():
    with patch("famiglia_core.command_center.backend.api.routes.operations.os.walk") as mock_walk:
        mock_walk.return_value = []
        response = client.post("/api/v1/graphs/non_existent/execute")
        assert response.status_code == 404
