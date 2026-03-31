import pytest
import os
from unittest.mock import MagicMock, patch
from famiglia_core.command_center.backend.mattermost.client import MattermostQueueClient

@pytest.fixture
def mock_redis(mocker):
    mock = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock)
    return mock

def test_mattermost_add_reaction_success(mock_redis, mocker):
    mock_driver = MagicMock()
    mocker.patch("famiglia_core.command_center.backend.mattermost.client.Driver", return_value=mock_driver)
    
    mock_driver.login.return_value = None
    mock_driver.users.get_user.return_value = {"id": "user_123"}
    
    with patch.dict("os.environ", {"MATTERMOST_BOT_TOKEN_ALFREDO": "fake-token"}):
        client = MattermostQueueClient()
        success = client.add_reaction("alfredo", "post_456", ":thumbsup:")
        
        assert success is True
        mock_driver.reactions.create_reaction.assert_called_once()

def test_mattermost_download_file_success(mock_redis, mocker):
    mock_driver = MagicMock()
    mocker.patch("famiglia_core.command_center.backend.mattermost.client.Driver", return_value=mock_driver)
    
    mock_driver.login.return_value = None
    mock_driver.files.get_file_info.return_value = {"name": "test_mm.png"}
    mock_response = MagicMock()
    mock_response.content = b"mattermost_file_data"
    mock_driver.files.get_file.return_value = mock_response
    
    with patch.dict("os.environ", {"MATTERMOST_BOT_TOKEN_ALFREDO": "fake-token"}):
        client = MattermostQueueClient()
        
        with patch("os.makedirs"), patch("builtins.open", mocker.mock_open()):
            path = client.download_file("f_999", "alfredo")
            assert path is not None
            assert "test_mm.png" in path

def test_mattermost_resolve_sender_name(mock_redis, mocker):
    mock_driver = MagicMock()
    mocker.patch("famiglia_core.command_center.backend.mattermost.client.Driver", return_value=mock_driver)
    
    mock_driver.login.return_value = None
    mock_driver.users.get_user.side_effect = [
        {"id": "bot_123", "username": "alfredo_bot"}, # During init
        {"id": "user_456", "username": "jimmy_mm"}    # During resolve
    ]
    
    with patch.dict("os.environ", {"MATTERMOST_BOT_TOKEN_ALFREDO": "fake-token"}):
        client = MattermostQueueClient()
        name = client.resolve_sender_name("user_456", "alfredo")
        assert name == "jimmy_mm"
