import sys
import os
from unittest.mock import MagicMock, patch

# Mock the database and slack_sdk before importing the service
sys.modules['famiglia_core.db.tools.user_connections_store'] = MagicMock()
sys.modules['slack_sdk'] = MagicMock()
sys.modules['slack_sdk.errors'] = MagicMock()

from famiglia_core.command_center.backend.comms.slack.provisioning import SlackProvisioningService

def test_sync_workspace_logic():
    service = SlackProvisioningService()
    
    # Mock user_connections_store
    with patch('famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store') as mock_store:
        # 1. Mock Alfredo's token
        mock_store.get_connection.side_effect = lambda service: {
            "slack_bot:alfredo": {"access_token": "xoxb-alfredo"},
            "slack_bot:riccardo": {"access_token": "xoxb-riccardo"},
            "slack_channel:ALFREDO_COMMAND": None, # Force creation
            "slack_channel:CODE_REVIEWS": {"access_token": "C123", "username": "old-name"} # Force rename
        }.get(service)

        # 2. Mock WebClient
        mock_client = MagicMock()
        with patch('famiglia_core.command_center.backend.comms.slack.provisioning.WebClient', return_value=mock_client):
            
            # auth_test returns user_id
            mock_client.auth_test.return_value = {"user_id": "U123"}
            
            # conversations_info returns channel info
            mock_client.conversations_info.return_value = {
                "ok": True,
                "channel": {"id": "C123", "name": "old-name"}
            }
            
            # conversations_list (for missing IDs)
            mock_client.conversations_list.return_value = {"ok": True, "channels": [], "response_metadata": {}}
            
            # conversations_create returns new channel
            mock_client.conversations_create.return_value = {
                "ok": True,
                "channel": {"id": "C999", "name": "alfredo-command"}
            }

            # Run sync
            results = service.sync_workspace_structure()
            
            # Verifications
            print("Sync Results:", results)
            
            # Check if create was called for ALFREDO_COMMAND
            mock_client.conversations_create.assert_any_call(name="alfredo-command")
            
            # Check if rename was called for CODE_REVIEWS (since it had 'old-name')
            mock_client.conversations_rename.assert_called_with(channel="C123", name="code-reviews")
            
            # Check if invite was called (Alfredo invites Riccardo, etc.)
            # Alfredo is in the registry for ALFREDO_COMMAND. Ricardo is in CODE_REVIEWS.
            # conversations_invite should be called for riccardo in C123
            # and for alfredo in C999
            
            invites = [call.args for call in mock_client.conversations_invite.call_args_list]
            print("Invites:", invites)
            
            assert any(call[0] == "C123" and "U123" in call[1] for call in mock_client.conversations_invite.call_args_list)

    print("✅ Logic test passed!")

if __name__ == "__main__":
    test_sync_workspace_logic()
