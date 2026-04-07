import pytest
import os
import requests
from unittest.mock import MagicMock, patch
from famiglia_core.command_center.backend.comms.slack.client import SlackQueueClient

@pytest.fixture
def mock_redis(mocker):
    mock = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock)
    return mock

def test_slack_download_file_success_header(mock_redis, mocker):
    client = SlackQueueClient()
    
    # Mock requests.get
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/png"}
    mock_response.iter_content.return_value = iter([b"chunk1", b"chunk2"])
    mocker.patch("requests.get", return_value=mock_response)
    
    file_info = {
        "url_private_download": "https://slack.com/file.png",
        "name": "test.png",
        "id": "F123"
    }
    
    with patch("os.makedirs"), patch("builtins.open", mocker.mock_open()):
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}):
            path = client.download_file(file_info, "alfredo")
            assert path is not None
            assert "test.png" in path

def test_slack_download_file_fallback_query(mock_redis, mocker):
    client = SlackQueueClient()
    
    # First call returns HTML (failure), second call returns 200 (success)
    mock_fail = MagicMock()
    mock_fail.status_code = 200
    mock_fail.iter_content.return_value = iter([b"<!DOCTYPE html>"]) # HTML detection
    
    mock_success = MagicMock()
    mock_success.status_code = 200
    mock_success.iter_content.return_value = iter([b"real_data"])
    
    mocker.patch("requests.get", side_effect=[mock_fail, mock_success])
    
    file_info = {"url_private": "https://slack.com/file.png", "name": "test.png"}
    
    with patch("os.makedirs"), patch("builtins.open", mocker.mock_open()):
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}):
            path = client.download_file(file_info, "alfredo")
            assert path is not None
            assert requests.get.call_count == 2

def test_slack_resolve_sender_name_cache(mock_redis):
    client = SlackQueueClient()
    client.user_name_cache["U123"] = "Cached Name"
    
    assert client.resolve_sender_name("U123") == "Cached Name"

@patch("famiglia_core.command_center.backend.comms.slack.client.WebClient")
def test_slack_resolve_sender_name_api(mock_web_client_cls, mock_redis):
    mock_client = MagicMock()
    mock_web_client_cls.return_value = mock_client
    mock_client.auth_test.return_value = {"user_id": "BOT123"}
    
    client = SlackQueueClient()
    client.clients = {"alfredo": mock_client}
    
    # Mock users_info response
    mock_client.users_info.return_value = {
        "user": {"profile": {"display_name": "API Name"}}
    }
    
    name = client.resolve_sender_name("U456")
    assert name == "API Name"
    assert client.user_name_cache["U456"] == "API Name"
