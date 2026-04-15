import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from famiglia_core.command_center.backend.api.main import app

client = TestClient(app)

CONNECTIONS_STORE = "famiglia_core.command_center.backend.api.routes.connections.user_connections_store"


# ─── /connections/config ──────────────────────────────────────────────────────

class TestGetConnectionsConfig:
    @patch("famiglia_core.command_center.backend.api.routes.connections.github_oauth_client")
    @patch("famiglia_core.command_center.backend.api.routes.connections.slack_oauth_client")
    @patch("famiglia_core.command_center.backend.api.routes.connections.notion_oauth_client")
    def test_returns_all_services(self, mock_notion, mock_slack, mock_github):
        mock_github.is_configured.return_value = True
        mock_github.redirect_uri = "http://localhost/auth/github/callback"
        mock_github.client_id = "gh_client_id"

        mock_slack.is_configured.return_value = False
        mock_slack.redirect_uri = "http://localhost/auth/slack/callback"
        mock_slack.client_id = None

        mock_notion.is_configured.return_value = False
        mock_notion.redirect_uri = "http://localhost/auth/notion/callback"
        mock_notion.client_id = None

        response = client.get("/api/v1/connections/config")
        assert response.status_code == 200
        data = response.json()
        assert data["github"]["configured"] is True
        assert data["github"]["client_id"] == "gh_client_id"
        assert data["slack"]["configured"] is False
        assert "notion" in data


# ─── POST /connections/ollama/key ─────────────────────────────────────────────

class TestSaveOllamaApiKey:
    @patch(CONNECTIONS_STORE)
    def test_saves_key_successfully(self, mock_store):
        mock_store.upsert_connection.return_value = True
        response = client.post("/api/v1/connections/ollama/key", json={"api_key": "sk-test-key"})
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_store.upsert_connection.assert_called_once_with(service="ollama", access_token="sk-test-key")

    @patch(CONNECTIONS_STORE)
    def test_trims_whitespace_from_key(self, mock_store):
        mock_store.upsert_connection.return_value = True
        response = client.post("/api/v1/connections/ollama/key", json={"api_key": "  sk-padded  "})
        assert response.status_code == 200
        mock_store.upsert_connection.assert_called_once_with(service="ollama", access_token="sk-padded")

    def test_rejects_empty_key(self):
        response = client.post("/api/v1/connections/ollama/key", json={"api_key": "   "})
        assert response.status_code == 422

    @patch(CONNECTIONS_STORE)
    def test_returns_500_when_store_fails(self, mock_store):
        mock_store.upsert_connection.return_value = False
        response = client.post("/api/v1/connections/ollama/key", json={"api_key": "sk-test-key"})
        assert response.status_code == 500


# ─── GET /connections/ollama/test ─────────────────────────────────────────────

class TestTestOllamaConnection:
    @patch("famiglia_core.command_center.backend.api.routes.connections.http_requests")
    @patch(CONNECTIONS_STORE)
    def test_success_returns_host_and_models(self, mock_store, mock_requests):
        mock_store.get_connection_status.return_value = {"connected": True}
        mock_store.get_connection.return_value = {"access_token": "sk-valid"}

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "gemma3:4b"}, {"name": "llama3:latest"}]}
        mock_requests.get.return_value = mock_response
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError

        response = client.get("/api/v1/connections/ollama/test")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "gemma3:4b" in data["models"]
        assert "llama3:latest" in data["models"]

    @patch(CONNECTIONS_STORE)
    def test_404_when_no_key_stored(self, mock_store):
        mock_store.get_connection_status.return_value = {"connected": False}
        response = client.get("/api/v1/connections/ollama/test")
        assert response.status_code == 404

    @patch(CONNECTIONS_STORE)
    def test_500_when_key_cannot_be_decrypted(self, mock_store):
        mock_store.get_connection_status.return_value = {"connected": True}
        mock_store.get_connection.return_value = None
        response = client.get("/api/v1/connections/ollama/test")
        assert response.status_code == 500

    @patch("famiglia_core.command_center.backend.api.routes.connections.http_requests")
    @patch(CONNECTIONS_STORE)
    def test_503_when_ollama_unreachable(self, mock_store, mock_requests):
        mock_store.get_connection_status.return_value = {"connected": True}
        mock_store.get_connection.return_value = {"access_token": "sk-valid"}
        mock_requests.get.side_effect = ConnectionError("refused")
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError

        response = client.get("/api/v1/connections/ollama/test")
        assert response.status_code == 503

    @patch("famiglia_core.command_center.backend.api.routes.connections.http_requests")
    @patch(CONNECTIONS_STORE)
    def test_504_when_ollama_times_out(self, mock_store, mock_requests):
        mock_store.get_connection_status.return_value = {"connected": True}
        mock_store.get_connection.return_value = {"access_token": "sk-valid"}
        mock_requests.get.side_effect = TimeoutError("timeout")
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError

        response = client.get("/api/v1/connections/ollama/test")
        assert response.status_code == 504

    @patch("famiglia_core.command_center.backend.api.routes.connections.http_requests")
    @patch(CONNECTIONS_STORE)
    def test_401_when_key_rejected_by_ollama(self, mock_store, mock_requests):
        mock_store.get_connection_status.return_value = {"connected": True}
        mock_store.get_connection.return_value = {"access_token": "sk-bad"}

        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response
        mock_requests.exceptions.ConnectionError = ConnectionError
        mock_requests.exceptions.Timeout = TimeoutError

        response = client.get("/api/v1/connections/ollama/test")
        assert response.status_code == 401


# ─── GET /connections/{service} ───────────────────────────────────────────────

class TestGetConnectionStatus:
    @patch(CONNECTIONS_STORE)
    def test_returns_connected_status(self, mock_store):
        mock_store.get_connection_status.return_value = {
            "connected": True,
            "connected_at": "2026-04-15T10:00:00+00:00",
        }
        response = client.get("/api/v1/connections/ollama")
        assert response.status_code == 200
        assert response.json()["connected"] is True

    @patch(CONNECTIONS_STORE)
    def test_returns_disconnected_when_not_found(self, mock_store):
        mock_store.get_connection_status.return_value = {"connected": False}
        response = client.get("/api/v1/connections/github")
        assert response.status_code == 200
        assert response.json()["connected"] is False


# ─── DELETE /connections/{service} ────────────────────────────────────────────

class TestDisconnectService:
    @patch(CONNECTIONS_STORE)
    def test_disconnect_succeeds(self, mock_store):
        mock_store.delete_connection.return_value = True
        response = client.delete("/api/v1/connections/ollama")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch(CONNECTIONS_STORE)
    def test_disconnect_returns_500_on_failure(self, mock_store):
        mock_store.delete_connection.return_value = False
        response = client.delete("/api/v1/connections/ollama")
        assert response.status_code == 500
