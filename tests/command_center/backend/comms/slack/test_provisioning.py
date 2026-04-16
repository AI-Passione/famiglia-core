import os
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open

from slack_sdk.errors import SlackApiError
from famiglia_core.command_center.backend.comms.slack.provisioning import SlackProvisioningService

class TestSlackProvisioningService:

    def setup_method(self):
        self.service = SlackProvisioningService()

    @patch.dict(os.environ, {"PUBLIC_URL": "https://custom-domain.com/"}, clear=True)
    def test_get_public_url_from_env(self):
        assert self.service._get_public_url() == "https://custom-domain.com"

    @patch.dict(os.environ, {}, clear=True)
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.requests.get")
    def test_get_public_url_from_ngrok(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "tunnels": [{"proto": "https", "public_url": "https://ngrok-test.com/"}]
        }
        mock_get.return_value = mock_response

        assert self.service._get_public_url() == "https://ngrok-test.com"

    @patch.dict(os.environ, {}, clear=True)
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.requests.get")
    def test_get_public_url_fails_gracefully(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        assert self.service._get_public_url() is None

    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store")
    def test_provision_famiglia_missing_token(self, mock_store):
        mock_store.get_connection.return_value = None
        with pytest.raises(ValueError, match="No Slack App Configuration Token found"):
            self.service.provision_famiglia()

    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store")
    def test_finalize_agent(self, mock_store):
        mock_store.upsert_connection.return_value = True
        
        result = self.service.finalize_agent("test_agent", "xoxb-123", "xapp-456")
        
        assert result is True
        assert mock_store.upsert_connection.call_count == 2
        
        mock_store.upsert_connection.assert_any_call(
            service="slack_bot:test_agent", access_token="xoxb-123"
        )
        mock_store.upsert_connection.assert_any_call(
            service="slack_socket:test_agent", access_token="xapp-456"
        )

    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.WebClient")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.os.listdir")
    def test_provision_famiglia_create_new(self, mock_listdir, mock_store, mock_web_client):
        # Mocking finding one manifest
        mock_listdir.return_value = ["test_agent.yaml"]
        
        # Mocking reading yaml
        yaml_content = """
display_information:
  name: Test Agent
settings:
  socket_mode_enabled: true
"""
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            # Set up mock Slack client response
            mock_client_instance = mock_web_client.return_value
            mock_client_instance.apps_manifest_create.return_value = {
                "ok": True,
                "app_id": "A12345678",
                "credentials": {
                    "client_id": "client_123",
                    "client_secret": "secret_456"
                }
            }

            # Return empty for no existing credentials
            mock_store.get_connection.return_value = None

            # Force socket mode
            self.service._get_public_url = MagicMock(return_value=None)

            result = self.service.provision_famiglia(app_level_token="xapp-setup")

            assert len(result) == 1
            app_info = result[0]
            assert app_info["agent_id"] == "test_agent"
            assert app_info["app_id"] == "A12345678"
            assert "https://api.slack.com/apps/A12345678" in app_info["install_url"]

            # Ensures DB upsert was called
            mock_store.upsert_connection.assert_called()

    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.WebClient")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.os.listdir")
    def test_provision_famiglia_update_existing_http_mode(self, mock_listdir, mock_store, mock_web_client):
        # Mocking finding one manifest
        mock_listdir.return_value = ["test_agent.yml"]
        
        # Mocking yaml content
        yaml_content = """
display_information:
  name: Test Agent
settings:
  socket_mode_enabled: true
"""
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            # Force HTTP Mode by setting public URL
            self.service._get_public_url = MagicMock(return_value="https://public.url")
            
            mock_client_instance = mock_web_client.return_value
            mock_client_instance.apps_manifest_update.return_value = {"ok": True}

            # Mock existing credentials in DB
            mock_store.get_connection.return_value = {
                "access_token": json.dumps({
                    "app_id": "A_EXISTS",
                    "client_id": "client_EXISTS",
                    "client_secret": "secret_EXISTS"
                })
            }

            result = self.service.provision_famiglia(app_level_token="xapp-setup")

            assert len(result) == 1
            app_info = result[0]
            assert app_info["app_id"] == "A_EXISTS"
            # It should have updated the manifest, not created
            mock_client_instance.apps_manifest_update.assert_called_once()
            
            # The install URL should point to oauth because of public_url being set
            assert "oauth/v2/authorize" in app_info["install_url"]
            assert "client_id=client_EXISTS" in app_info["install_url"]
