import pytest
import json
from unittest.mock import MagicMock, patch
from famiglia_core.command_center.backend.mattermost.client import MattermostQueueClient, PRIORITY_HIGH

def test_mattermost_enqueue_message():
    # Mock redis
    mock_redis = MagicMock()
    with patch("redis.from_url", return_value=mock_redis):
        client = MattermostQueueClient()
        
        # Enqueue a message
        client.enqueue_message("alfredo", "channel_id_123", "Hello Mattermost!", PRIORITY_HIGH)
        
        # Verify redis rpush
        assert mock_redis.rpush.call_count == 1
        call_args = mock_redis.rpush.call_args[0]
        assert call_args[0] == f"mattermost:queue:{PRIORITY_HIGH}"
        payload = json.loads(call_args[1])
        assert payload["agent"] == "alfredo"
        assert payload["message"] == "Hello Mattermost!"

def test_mattermost_post_message_mock():
    # Mock redis and Driver
    mock_redis = MagicMock()
    mock_driver = MagicMock()
    
    with patch("redis.from_url", return_value=mock_redis), \
         patch("famiglia_core.command_center.backend.mattermost.client.Driver", return_value=mock_driver):
        
        # Setup mock driver behavior
        mock_driver.login.return_value = None
        mock_driver.users.get_user.return_value = {"id": "user_id_123", "username": "alfredo_bot"}
        mock_driver.posts.create_post.return_value = {"id": "post_id_456"}
        
        # Initialize client with alfredo token
        with patch.dict("os.environ", {"MATTERMOST_BOT_TOKEN_ALFREDO": "fake-token"}):
            client = MattermostQueueClient()
            
            # Post a message
            post_id = client.post_message("alfredo", "channel_id_789", "Test message")
            
            assert post_id == "post_id_456"
            mock_driver.posts.create_post.assert_called_once_with({
                'channel_id': 'channel_id_789',
                'message': 'Test message',
                'root_id': None
            })

if __name__ == "__main__":
    # This allows running the test directly if needed
    pytest.main([__file__])
