import sys
from unittest.mock import MagicMock, patch

# Mock the database and slack_sdk before importing the service
sys.modules['famiglia_core.db.tools.user_connections_store'] = MagicMock()
sys.modules['slack_sdk'] = MagicMock()
sys.modules['slack_sdk.errors'] = MagicMock()

from famiglia_core.command_center.backend.comms.slack.provisioning import SlackProvisioningService

def test_sync_workspace_logic():
    service = SlackProvisioningService()
    # Mock context_store
    service._seed_agent_greetings = MagicMock()
    # Mock user_connections_store
    with patch('famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store') as mock_store:
        # 1. Mock Alfredo's token and others
        mock_store.get_connection.side_effect = lambda service: {
            "slack_bot:alfredo": {"access_token": "xoxb-alfredo"},
            "slack_bot:riccardo": {"access_token": "xoxb-riccardo"},
            "slack_owner": {"access_token": "U_OWNER"},
            "slack_channel:COMMAND_CENTER": None, # Force creation
            "slack_channel:TECH": {"access_token": "C123", "username": "old-name"}, # Force rename
            "slack_channel:PRODUCT_STRATEGY": {"access_token": "C505", "username": "old-product"} # Force rename
        }.get(service)

        # Mock list_connections to include a STALE channel
        mock_store.list_connections.return_value = {
            "slack_channel:TECH": {"access_token": "C123", "username": "old-name"},
            "slack_channel:STALE_CHANNEL": {"access_token": "C404", "username": "stale"},
            "slack_channel:PRODUCT_STRATEGY": {"access_token": "C505", "username": "old-product"}
        }

        # 2. Mock WebClient
        mock_client = MagicMock()
        with patch('famiglia_core.command_center.backend.comms.slack.provisioning.WebClient', return_value=mock_client):
            
            # auth_test returns user_id
            mock_client.auth_test.return_value = {"user_id": "U123"}
            
            # users_list returns members
            mock_client.users_list.return_value = {
                "ok": True,
                "members": [
                    {"id": "U_PRIMARY", "is_primary_owner": True, "real_name": "The Don"}
                ]
            }

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
                "channel": {"id": "C999", "name": "command-center"}
            }

            # Run sync
            results = service.sync_workspace_structure()
            
            # Verifications
            print("Sync Results:", results)
            
            # Check if archive was called for STALE_CHANNEL
            mock_client.conversations_archive.assert_called_with(channel="C404")
            mock_store.delete_connection.assert_any_call("slack_channel:STALE_CHANNEL")

            # Check if create was called for COMMAND_CENTER
            mock_client.conversations_create.assert_any_call(name="command-center")
            
            # Check if rename was called for TECH (since it had 'old-name')
            mock_client.conversations_rename.assert_any_call(channel="C123", name="tech")
            
            # Check if rename was called for PRODUCT_STRATEGY
            mock_client.conversations_rename.assert_any_call(channel="C505", name="product")
            
            # Check if invite was called (Alfredo invites Owner, then Riccardo, etc.)
            invites = [call.kwargs for call in mock_client.conversations_invite.call_args_list]
            print("Invites:", invites)
            
            # Should have invited U_OWNER (from store)
            assert any(call.kwargs.get("channel") == "C123" and call.kwargs.get("users") == "U_OWNER" for call in mock_client.conversations_invite.call_args_list)
            assert any(call.kwargs.get("channel") == "C999" and call.kwargs.get("users") == "U_OWNER" for call in mock_client.conversations_invite.call_args_list)

            # verify bot join
            assert any(call.kwargs.get("channel") == "C123" and call.kwargs.get("users") == "U123" for call in mock_client.conversations_invite.call_args_list)

            # --- Test Case 2: Programmatic Discovery ---
            print("\n--- Testing Programmatic Discovery ---")
            mock_client.conversations_invite.reset_mock()
            mock_store.get_connection.side_effect = lambda service: {
                "slack_bot:alfredo": {"access_token": "xoxb-alfredo"},
                "slack_owner": None # Force discovery
            }.get(service)
            
            service.sync_workspace_structure()
            invites2 = [call.kwargs for call in mock_client.conversations_invite.call_args_list]
            
            # Should have discovered and invited U_PRIMARY (from users_list mock)
            assert any(invite.get("users") == "U_PRIMARY" for invite in invites2)
            # Verify it was cached in DB
            mock_store.upsert_connection.assert_any_call(service="slack_owner", access_token="U_PRIMARY")

    print("✅ Logic test passed!")

if __name__ == "__main__":
    test_sync_workspace_logic()
