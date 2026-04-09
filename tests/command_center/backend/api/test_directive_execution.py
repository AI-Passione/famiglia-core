from fastapi.testclient import TestClient
from unittest.mock import patch

from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
def test_execute_directive_with_graph(mock_store):
    """Test that providing a graph_id routes to the correct agent and creates a task."""
    # Mock task creation
    mock_store.create_scheduled_task.return_value = {
        "id": 123,
    }
    
    payload = {"graph_id": "simple_data_analysis"}
    response = client.post("/api/v1/operations/directive/execute", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 123
    assert "Kowalski" in data["message"]
    
    # Verify task creation args
    mock_store.create_scheduled_task.assert_called_once()
    _, kwargs = mock_store.create_scheduled_task.call_args
    assert kwargs["metadata"]["agent_id"] == "kowalski"
    assert kwargs["metadata"]["graph_id"] == "simple_data_analysis"

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
def test_execute_directive_manual_routing(mock_store):
    """Test that manual prompt keywords route to the correct agent."""
    mock_store.create_scheduled_task.return_value = {"id": 456}
    
    # Keyword 'code' should route to Riccardo
    payload = {"manual_prompt": "Please optimize the database code"}
    response = client.post("/api/v1/operations/directive/execute", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "Riccardo" in data["message"]
    
    _, kwargs = mock_store.create_scheduled_task.call_args
    assert kwargs["metadata"]["agent_id"] == "riccardo"

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
def test_execute_directive_default_routing(mock_store):
    """Test that manual prompt without keywords routes to Alfredo."""
    mock_store.create_scheduled_task.return_value = {"id": 789}
    
    payload = {"manual_prompt": "Hello world"}
    response = client.post("/api/v1/operations/directive/execute", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "Alfredo" in data["message"]
    
    _, kwargs = mock_store.create_scheduled_task.call_args
    assert kwargs["metadata"]["agent_id"] == "alfredo"

def test_execute_directive_missing_params():
    """Test that missing params returns 400."""
    response = client.post("/api/v1/operations/directive/execute", json={})
    assert response.status_code == 400
    assert "Missing graph_id or manual_prompt" in response.json()["detail"]

@patch("famiglia_core.command_center.backend.api.routes.operations.context_store")
def test_execute_directive_message_logging(mock_store):
    """Test that an acknowledgement message is logged for the agent."""
    mock_store.create_scheduled_task.return_value = {"id": 111}
    
    payload = {"graph_id": "code_implementation"}
    response = client.post("/api/v1/operations/directive/execute", json=payload)
    
    assert response.status_code == 200
    # Verify log_message was called for the agent (Riccardo)
    mock_store.log_message.assert_called()
    _, kwargs = mock_store.log_message.call_args
    assert kwargs["agent_name"] == "riccardo"
    assert "Understood" in kwargs["content"]

@patch("famiglia_core.command_center.backend.api.routes.operations.graph_parser")
def test_get_graphs_discovery(mock_parser):
    """Test that the discovery endpoint returns graphs from the parser."""
    mock_parser.parse_all_graphs.return_value = [
        {
            "id": "test_graph", 
            "name": "Test Graph", 
            "category": "Testing",
            "nodes": [],
            "edges": []
        }
    ]
    
    response = client.get("/api/v1/operations/graphs")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test_graph"
    assert data[0]["category"] == "Testing"
