import pytest
import json
import yaml
from unittest.mock import MagicMock, patch, mock_open
from famiglia_core.command_center.backend.comms.slack.provisioning import SlackProvisioningService

class TestSlackProvisioningService:
    @pytest.fixture
    def service(self):
        return SlackProvisioningService()

    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.os.listdir")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.os.path.exists")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.WebClient")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store")
    def test_provision_http_mode_detection(self, mock_store, mock_web_client_cls, mock_exists, mock_listdir, service):
        # Mocking
        mock_listdir.return_value = ["alfredo.yaml"]
        mock_exists.return_value = True
        mock_client = MagicMock()
        mock_web_client_cls.return_value = mock_client
        
        # Manifest content
        dummy_manifest = {
            "display_information": {"name": "Alfredo"},
            "settings": {"socket_mode_enabled": True}
        }
        
        # Mock public URL (Choice B)
        with patch.object(service, "_get_public_url", return_value="https://famiglia.ngrok.io"):
            with patch("builtins.open", mock_open(read_data=yaml.dump(dummy_manifest))):
                mock_client.apps_manifest_create.return_value = {
                    "ok": True,
                    "app_id": "A123",
                    "credentials": {"client_id": "C123", "client_secret": "S123"}
                }
                
                service.provision_famiglia(app_level_token="xapp-test")
                
                # Verify manifest patching
                args = mock_client.apps_manifest_create.call_args[1]["manifest"]
                manifest_data = yaml.safe_load(args)
                assert manifest_data["settings"]["socket_mode_enabled"] is False
                
                # Verify metadata storage
                mock_store.upsert_connection.assert_called()
                call_args = mock_store.upsert_connection.call_args[1]
                metadata = json.loads(call_args["access_token"])
                assert metadata["transport"] == "http"
                assert metadata["public_url"] == "https://famiglia.ngrok.io"

    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.os.listdir")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.WebClient")
    @patch("famiglia_core.command_center.backend.comms.slack.provisioning.user_connections_store")
    def test_provision_socket_mode_fallback(self, mock_store, mock_web_client_cls, mock_listdir, service):
        mock_listdir.return_value = ["alfredo.yaml"]
        mock_client = MagicMock()
        mock_web_client_cls.return_value = mock_client
        
        dummy_manifest = {
            "display_information": {"name": "Alfredo"},
            "settings": {"socket_mode_enabled": True}
        }
        
        # No public URL (Choice A)
        with patch.object(service, "_get_public_url", return_value=None):
            with patch("builtins.open", mock_open(read_data=yaml.dump(dummy_manifest))):
                mock_client.apps_manifest_create.return_value = {
                    "ok": True,
                    "app_id": "A123",
                    "credentials": {"client_id": "C123", "client_secret": "S123"}
                }
                
                service.provision_famiglia(app_level_token="xapp-test")
                
                # Verify socket mode kept
                args = mock_client.apps_manifest_create.call_args[1]["manifest"]
                manifest_data = yaml.safe_load(args)
                assert manifest_data["settings"]["socket_mode_enabled"] is True
                
                # Verify metadata storage
                call_args = mock_store.upsert_connection.call_args[1]
                metadata = json.loads(call_args["access_token"])
                assert metadata["transport"] == "socket"
                assert metadata["public_url"] is None
