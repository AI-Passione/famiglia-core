import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from famiglia_core.command_center.backend.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.complete_task.return_value = "This is a test response from the agent."
    return agent

def test_chat_standard_endpoint(client, mocker, mock_agent):
    # Setup mocks
    mock_agent_manager = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.agent_manager")
    mock_user_service = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.user_service")
    
    mock_agent_manager.get_agent.return_value = mock_agent
    mock_user_service.get_don.return_value = {"id": 1, "full_name": "Don Jimmy"}
    
    payload = {
        "message": "Hello Alfredo!",
        "agent_id": "alfredo",
        "platform": "web"
    }
    
    response = client.post("/api/v1/chat/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "alfredo"
    assert "test response" in data["message"]
    assert data["status"] == "success"
    
    mock_agent.complete_task.assert_called_once()

def test_chat_stream_endpoint(client, mocker, mock_agent):
    # Setup mocks
    mock_agent_manager = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.agent_manager")
    mock_user_service = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.user_service")
    
    mock_agent_manager.get_agent.return_value = mock_agent
    mock_user_service.get_don.return_value = {"id": 1, "full_name": "Don Jimmy"}
    
    # Mock complete_task to return a string (it runs in executor)
    mock_agent.complete_task.return_value = "Final streaming response."
    
    # We test the SSE endpoint
    params = {
        "message": "Stream hello!",
        "agent_id": "alfredo"
    }
    
    with client.stream("GET", "/api/v1/chat/stream", params=params) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

def test_upload_file_endpoint(client, mocker):
    # Setup mocks
    mock_agent_manager = mocker.patch("famiglia_core.command_center.backend.api.routes.chat.agent_manager")
    
    # Mocking the agent object
    mock_agent = MagicMock()
    mock_agent_manager.get_agent.return_value = mock_agent
    
    from io import BytesIO
    file_content = b"hello world"
    file_obj = BytesIO(file_content)
    
    response = client.post(
        "/api/v1/chat/upload",
        params={"agent_id": "alfredo"},
        files={"file": ("test.txt", file_obj, "application/octet-stream")}
    )
    
    if response.status_code != 200:
        print(f"DEBUG Response: {response.text}")
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert "test.txt" in json_data["filename"]
