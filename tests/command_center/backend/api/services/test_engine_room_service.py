import json
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from famiglia_core.command_center.backend.api.services.engine_room_service import EngineRoomService

class TestEngineRoomService(unittest.TestCase):
    def setUp(self):
        self.service = EngineRoomService()

    @patch("socket.gethostname")
    @patch("platform.system")
    @patch("os.getloadavg")
    @patch("shutil.disk_usage")
    def test_get_snapshot_structure(self, mock_disk, mock_load, mock_system, mock_hostname):
        # Setup mocks
        mock_hostname.return_value = "test-host"
        mock_system.return_value = "Linux"
        mock_load.return_value = (0.1, 0.2, 0.3)
        mock_disk.return_value = MagicMock(total=1000, used=400, free=600)
        
        with patch.object(self.service, "_read_memory_snapshot") as mock_mem:
            mock_mem.return_value = {"total_bytes": 100, "usage_percent": 10}
            
            snapshot = self.service.get_snapshot()
            
            self.assertIn("generated_at", snapshot)
            self.assertEqual(snapshot["host"]["hostname"], "test-host")
            self.assertEqual(snapshot["host"]["disk"]["total_bytes"], 1000)

    @patch("urllib.request.urlopen")
    def test_fetch_ollama_models_success(self, mock_url_open):
        # Mock successful JSON response from Ollama
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "gemma:2b"},
                {"name": "llama3:latest"}
            ]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_url_open.return_value = mock_response

        with patch.dict(os.environ, {"OLLAMA_HOST": "http://ollama:11434"}):
            result = self.service._fetch_ollama_models()
            self.assertIn("Models: gemma:2b, llama3:latest", result)

    @patch("urllib.request.urlopen")
    def test_fetch_ollama_models_failure(self, mock_url_open):
        # Mock failure (timeout or connection error)
        import urllib.error
        mock_url_open.side_effect = urllib.error.URLError("Connection refused")

        with patch.dict(os.environ, {"OLLAMA_HOST": "http://ollama:11434"}):
            result = self.service._fetch_ollama_models()
            # Should return the host URL as fallback
            self.assertEqual(result, "http://ollama:11434")

    @patch("subprocess.run")
    def test_read_docker_compose_state_not_installed(self, mock_run):
        # Mock FileNotFoundError for docker command
        mock_run.side_effect = FileNotFoundError

        state = self.service._read_docker_compose_state()
        self.assertFalse(state["available"])
        self.assertIn("Docker CLI not installed.", state["diagnostics"])

    @patch("subprocess.run")
    def test_read_docker_compose_state_success(self, mock_run):
        # Mock successful docker compose ps output
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = json.dumps([
            {"Service": "app", "State": "running", "Health": "healthy"},
            {"Service": "ollama", "State": "running", "Health": "starting"}
        ])
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        state = self.service._read_docker_compose_state()
        self.assertTrue(state["available"])
        self.assertEqual(len(state["services"]), 2)
        self.assertEqual(state["services"][0]["name"], "app")
        self.assertEqual(state["services"][0]["health"], "healthy")

if __name__ == "__main__":
    unittest.main()
