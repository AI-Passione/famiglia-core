import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timezone
from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

@patch("famiglia_core.command_center.backend.api.routes.intelligence.intelligence_service")
def test_list_intelligence_items(mock_service):
    mock_service.list_items.return_value = [
        {
            "id": 1,
            "title": "Test Dossier",
            "content": "Test Content",
            "summary": "Test Summary",
            "status": "Active",
            "item_type": "dossier",
            "reference_id": "REF-001",
            "metadata": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]
    response = client.get("/api/v1/intelligence/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test Dossier"
    mock_service.list_items.assert_called_once_with(None)

@patch("famiglia_core.command_center.backend.api.routes.intelligence.intelligence_service")
def test_get_intelligence_item(mock_service):
    mock_service.get_item.return_value = {
        "id": 1,
        "title": "Test Dossier",
        "content": "Test Content",
        "summary": "Test Summary",
        "status": "Active",
        "item_type": "dossier",
        "reference_id": "REF-001",
        "metadata": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    response = client.get("/api/v1/intelligence/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    mock_service.get_item.assert_called_once_with(1)

@patch("famiglia_core.command_center.backend.api.routes.intelligence.intelligence_service")
def test_create_intelligence_item(mock_service):
    mock_service.create_item.return_value = {
        "id": 1,
        "title": "New Item",
        "content": "New Content",
        "summary": "New Summary",
        "status": "Drafted",
        "item_type": "blueprint",
        "reference_id": "REF-NEW",
        "metadata": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    payload = {
        "title": "New Item",
        "content": "New Content",
        "summary": "New Summary",
        "status": "Drafted",
        "item_type": "blueprint",
        "reference_id": "REF-NEW",
        "metadata": {}
    }
    response = client.post("/api/v1/intelligence/", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "New Item"
    mock_service.create_item.assert_called_once()

@patch("famiglia_core.command_center.backend.api.routes.intelligence.intelligence_service")
def test_update_intelligence_item(mock_service):
    mock_service.update_item.return_value = {
        "id": 1,
        "title": "Updated Item",
        "content": "Updated Content",
        "summary": "Updated Summary",
        "status": "Active",
        "item_type": "dossier",
        "reference_id": "REF-001",
        "metadata": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    payload = {"title": "Updated Item"}
    response = client.patch("/api/v1/intelligence/1", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Item"
    mock_service.update_item.assert_called_once()

@patch("famiglia_core.command_center.backend.api.routes.intelligence.intelligence_service")
def test_delete_intelligence_item(mock_service):
    mock_service.delete_item.return_value = True
    response = client.delete("/api/v1/intelligence/1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_service.delete_item.assert_called_once_with(1)
