import pytest
import re
from unittest.mock import MagicMock, patch
from famiglia_core.command_center.backend.comms.slack.client import SlackQueueClient

@pytest.fixture
def mock_redis(mocker):
    mock = mocker.MagicMock()
    mocker.patch("redis.from_url", return_value=mock)
    return mock

@pytest.fixture
def client(mock_redis, mocker):
    # Prevent background thread and DB calls during init
    mocker.patch("famiglia_core.command_center.backend.comms.slack.client.SlackQueueClient._lookup_slack_user_name", return_value="Test User")
    mocker.patch("famiglia_core.db.tools.user_connections_store.user_connections_store.list_connections", return_value={})
    
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-default"}):
        c = SlackQueueClient()
        # Manually inject a client for 'rossini' but not for 'Dr. Rossini'
        mock_web_client = MagicMock()
        c.clients = {"rossini": mock_web_client}
        return c

def test_agent_name_normalization_rossini(client):
    """Verify that 'Dr. Rossini' and other variants resolve to 'rossini'."""
    payload = {
        "agent": "Dr. Rossini",
        "channel": "C123",
        "message": "Hello world"
    }
    
    with patch.object(client, "upload_file", return_value=False):
        # We don't want to actually send, just check which client is used
        # Mock _send_to_slack's dependencies
        client.clients["rossini"].chat_postMessage.return_value = {"ts": "1234.5678"}
        
        ts = client._send_to_slack(payload)
        
        # Verify that the 'rossini' client's chat_postMessage was called
        assert ts == "1234.5678"
        client.clients["rossini"].chat_postMessage.assert_called_once()

def test_lazy_refresh_on_cache_miss(client, mocker):
    """Verify that a missing agent triggers a DB refresh."""
    payload = {
        "agent": "new_agent",
        "channel": "C123",
        "message": "Hello"
    }
    
    # Mock refresh_bot_id to simulate finding the agent in DB
    def side_effect(agent_id):
        if agent_id == "new_agent":
            client.clients["new_agent"] = MagicMock()
            client.clients["new_agent"].chat_postMessage.return_value = {"ts": "999"}
            return "U_NEW"
        return None
        
    mocker.patch.object(client, "refresh_bot_id", side_effect=side_effect)
    
    ts = client._send_to_slack(payload)
    
    assert ts == "999"
    assert "new_agent" in client.clients
    client.refresh_bot_id.assert_called_with("new_agent")

def test_format_agent_message_minimalist(client):
    """Verify that the Block Kit layout is minimalist (no headers)."""
    blocks = client.format_agent_message("rossini", "My response")
    
    # blocks[0] should be the section with the text "My response"
    # Previously blocks[0] was the header, blocks[1] was divider, blocks[2] was text.
    assert len(blocks) >= 2
    assert blocks[0]["type"] == "section"
    assert blocks[0]["text"]["text"] == "My response"
    
    # Verify footer doesn't have "Agent: Rossini"
    footer = blocks[-1]
    if footer["type"] == "context":
        footer_text = footer["elements"][0]["text"]
        assert "Agent: Rossini" not in footer_text
        assert "La Famiglia Core" in footer_text

def test_user_connections_store_decryption_error_logging(mocker):
    """Verify that decryption errors are logged to stdout."""
    from famiglia_core.db.tools.user_connections_store import UserConnectionsStore
    
    # 1. Mock the encryption provider to force a failure
    mock_fernet = MagicMock()
    mock_fernet.decrypt.side_effect = Exception("Mock decryption error")
    mocker.patch("famiglia_core.db.tools.user_connections_store._get_fernet", return_value=mock_fernet)
    
    # 2. Mock print
    mock_print = mocker.patch("builtins.print")
    
    # 3. Create a mock cursor with a row to "decrypt"
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"service": "slack_bot:broken", "access_token": "garbage", "app_id": "A123", "connected_at": None, "username": "broken_bot", "avatar_url": None, "scopes": None}
    ]
    
    # 4. Mock the context manager db_session on the context_store instance
    # We patch it where it is imported in user_connections_store
    mock_session = mocker.patch("famiglia_core.db.tools.user_connections_store.context_store.db_session")
    mock_session.return_value.__enter__.return_value = mock_cursor
    
    store = UserConnectionsStore()
    results = store.list_connections("slack_bot:")
    
    # 5. Verify that print was called with the failure message
    found = False
    for call in mock_print.call_args_list:
        if "Failed to decrypt service 'slack_bot:broken'" in str(call):
            found = True
            break
    
    # If not found, let's see what was printed in the error message for debugging
    if not found:
        print(f"DEBUG: print calls: {mock_print.call_args_list}")
        
    assert found
    assert "slack_bot:broken" not in results
