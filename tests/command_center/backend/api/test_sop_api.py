from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timezone
from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

@patch("famiglia_core.command_center.backend.api.routes.sop.context_store")
def test_list_categories(mock_store):
    mock_store.list_workflow_categories.return_value = [
        {"id": 1, "name": "market_research", "display_name": "Market Research", "created_at": datetime.now(timezone.utc)},
        {"id": 2, "name": "analytics", "display_name": "Analytics", "created_at": datetime.now(timezone.utc)}
    ]
    
    response = client.get("/api/v1/sop/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["display_name"] == "Market Research"

@patch("famiglia_core.command_center.backend.api.routes.sop.context_store")
def test_create_category(mock_store):
    mock_store.create_workflow_category.return_value = {
        "id": 3, 
        "name": "new_ops", 
        "display_name": "New Ops", 
        "created_at": datetime.now(timezone.utc)
    }
    
    payload = {"name": "new_ops", "display_name": "New Ops"}
    response = client.post("/api/v1/sop/categories", json=payload)
    
    assert response.status_code == 200
    assert response.json()["display_name"] == "New Ops"
    mock_store.create_workflow_category.assert_called_once_with(name="new_ops", display_name="New Ops")

@patch("famiglia_core.command_center.backend.api.routes.sop.context_store")
def test_list_workflows(mock_store):
    # Mocking list_sop_workflows which returns a list of dicts
    mock_store.list_sop_workflows.return_value = [
        {"id": 1, "name": "test_sop", "category_id": 1}
    ]
    # Mocking get_sop_workflow which is called for each workflow in the list
    mock_store.get_sop_workflow.return_value = {
        "id": 1,
        "name": "test_sop",
        "display_name": "Test SOP",
        "category_id": 1,
        "category_name": "market_research",
        "category_display_name": "Market Research",
        "node_order": ["node1"],
        "nodes": [{"node_name": "node1", "node_type": "task", "description": "test"}],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    response = client.get("/api/v1/sop/workflows")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "Test SOP"

@patch("famiglia_core.command_center.backend.api.routes.sop.context_store")
def test_execute_sop(mock_store):
    mock_store.get_sop_workflow.return_value = {
        "id": 1,
        "name": "test_sop",
        "display_name": "Test SOP"
    }
    mock_store.create_scheduled_task.return_value = {"id": 123}
    
    response = client.post("/api/v1/sop/workflows/1/execute")
    assert response.status_code == 200
    assert response.json()["task_id"] == 123
    assert "dispatched" in response.json()["message"]
