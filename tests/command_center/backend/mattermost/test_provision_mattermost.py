import pytest
import json
import os
from unittest.mock import MagicMock, patch, mock_open
from famiglia_core.command_center.backend.mattermost.provision_mattermost import setup_mattermost

@pytest.fixture
def mock_driver_cls(mocker):
    return mocker.patch("famiglia_core.command_center.backend.mattermost.provision_mattermost.Driver")

@pytest.fixture
def mock_requests(mocker):
    return mocker.patch("famiglia_core.command_center.backend.mattermost.provision_mattermost.requests")

def test_setup_mattermost_full_flow(mock_driver_cls, mock_requests, mocker):
    mock_driver = MagicMock()
    mock_driver_cls.return_value = mock_driver
    
    # Mock driver methods
    mock_driver.login.return_value = None
    mock_driver.teams.get_team_by_name.return_value = {"id": "team_1", "name": "famiglia"}
    mock_driver.users.get_user_by_username.return_value = {"id": "user_1"}
    mock_driver.channels.get_channel_by_name.return_value = {"id": "chan_1"}
    
    # Mock bot creation response
    mock_bot_resp = MagicMock()
    mock_bot_resp.json.return_value = {"user_id": "bot_1"}
    mock_driver.client.make_request.return_value = mock_bot_resp
    
    # Mock provisioning_config.json
    config_data = {
        "team": {"name": "famiglia", "display_name": "La Famiglia"},
        "channels": [{"name": "prio", "display_name": "PRIO"}],
        "users": ["don_jimmy"],
        "bots": [{"username": "alfredo", "display_name": "Alfredo", "channels": ["prio"]}],
        "sidebar_categories": []
    }
    
    with patch("builtins.open", mock_open(read_data=json.dumps(config_data))):
        with patch.dict("os.environ", {
            "MATTERMOST_BOT_TOKEN_SYSTEM": "valid-token",
            "MATTERMOST_URL": "http://mattermost:8065"
        }):
            # Run setup (ensure it doesn't sys.exit by mocking sys.exit)
            with patch("sys.exit"):
                setup_mattermost()
                
                # Verify key interactions
                mock_driver.login.assert_called_once()
                mock_driver.teams.get_team_by_name.assert_called_with("famiglia")
                mock_driver.channels.get_channel_by_name.assert_called()
                mock_driver.logout.assert_called_once()

def test_setup_mattermost_missing_token(mock_driver_cls):
    with patch.dict("os.environ", {"MATTERMOST_BOT_TOKEN_SYSTEM": "your-system-token"}):
        with patch("sys.exit") as mock_exit:
            setup_mattermost()
            mock_exit.assert_called_once_with(1)
