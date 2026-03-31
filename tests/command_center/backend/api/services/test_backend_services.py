import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.command_center.backend.api.services.user_service import UserService
from famiglia_core.command_center.backend.api.services.agent_manager import AgentManager

@patch("famiglia_core.command_center.backend.api.services.user_service.context_store")
def test_user_service_get_don(mock_store):
    mock_cursor = MagicMock()
    mock_store.db_session.return_value.__enter__.return_value = mock_cursor
    
    # Mocking standard Don profile
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "full_name": "Don Jimmy",
        "username": "don_jimmy",
        "role": "don"
    }
    
    service = UserService()
    don = service.get_don()
    assert don["username"] == "don_jimmy"
    assert don["role"] == "don"

@patch("famiglia_core.command_center.backend.api.services.user_service.context_store")
def test_user_service_get_by_platform(mock_store):
    mock_cursor = MagicMock()
    mock_store.db_session.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchone.return_value = {
        "id": 1,
        "username": "don_jimmy",
        "platform_user_id": "U123456"
    }
    
    service = UserService()
    user = service.get_user_by_platform_id("slack", "U123456")
    assert user["username"] == "don_jimmy"
    assert user["platform_user_id"] == "U123456"

def test_agent_manager_singleton_and_listing():
    manager = AgentManager()
    
    # Mocking the actual class in the manager's registry
    mock_alfredo_cls = MagicMock()
    mock_alfredo_instance = MagicMock(name="AlfredoInstance")
    mock_alfredo_cls.return_value = mock_alfredo_instance
    
    manager._agent_classes["alfredo"] = mock_alfredo_cls
    
    alfredo1 = manager.get_agent("alfredo")
    alfredo2 = manager.get_agent("alfredo")
    
    assert alfredo1 == alfredo2
    assert mock_alfredo_cls.call_count == 1
    
    # Check non-existent agent
    assert manager.get_agent("unknown_agent") is None
