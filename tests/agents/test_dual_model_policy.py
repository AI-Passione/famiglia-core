import json
import unittest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.llm.client import LLMClient

class TestDualModelPolicy(unittest.TestCase):
    def setUp(self):
        self.client = LLMClient()
        self.client.default_ollama_model = "gemma3:4b"
        self.client.ollama_host = "http://localhost:11434"

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_ensure_offloaded_strict_policy(self, mock_request, mock_urlopen):
        # Setup mock for /api/ps
        mock_ps_response = MagicMock()
        # Mocking 3 models loaded: default, previous on-demand, and something else
        # Default: gemma3:4b (canonicalized)
        # Previous on-demand: phi3:mini
        # Something else: llama3
        mock_ps_response.read.return_value = json.dumps({
            "models": [
                {"name": "gemma3:4b"},
                {"name": "phi3:mini"},
                {"name": "llama3"}
            ]
        }).encode("utf-8")
        mock_ps_response.__enter__.return_value = mock_ps_response
        
        # We need to mock urlopen to return the PS response first, then success for evictions
        mock_urlopen.side_effect = [mock_ps_response, MagicMock(), MagicMock()]

        # Target model is phi3:mini (we want to use it)
        # Expected behavior: llama3 should be evicted. gemma3:4b (default) and phi3:mini (target) should NOT.
        
        with patch("builtins.print") as mock_print:
            self.client._ensure_offloaded(target_model="phi3:mini")
            
            # Check evictions
            eviction_calls = []
            for call in mock_request.call_args_list:
                args, kwargs = call
                # Handle both positional and keyword arguments
                data_json = kwargs.get('data') or (args[1] if len(args) > 1 else None)
                if data_json:
                    data = json.loads(data_json)
                    if data.get("keep_alive") == 0:
                        eviction_calls.append(data.get("model"))
            
            self.assertIn("llama3", eviction_calls)
            self.assertNotIn("gemma3:4b", eviction_calls)
            self.assertNotIn("phi3:mini", eviction_calls)
            self.assertNotIn("gemma3", eviction_calls) # Canonicalized check

    @patch("urllib.request.urlopen")
    def test_ollama_complete_keep_alive(self, mock_urlopen):
        # Mock pull and offload
        self.client._ensure_model_pulled = MagicMock()
        self.client._ensure_offloaded = MagicMock()
        
        # Mock generation response
        mock_gen_response = MagicMock()
        mock_gen_response.__iter__.return_value = [
            json.dumps({"response": "Hello", "done": True}).encode("utf-8")
        ]
        mock_gen_response.__enter__.return_value = mock_gen_response
        mock_urlopen.return_value = mock_gen_response

        # Use patch to capture the Request object sent to urlopen
        with patch("urllib.request.Request") as mock_request_class:
            self.client._ollama_complete("test prompt", model="phi3:mini")
            
            # Check keep_alive in the last request created
            # The first call is likely for /api/generate
            payload = json.loads(mock_request_class.call_args[1]['data'].decode('utf-8'))
            self.assertEqual(payload['keep_alive'], 60)

            # Test default model keep_alive
            self.client._ollama_complete("test prompt", model="gemma3:4b")
            payload_default = json.loads(mock_request_class.call_args[1]['data'].decode('utf-8'))
            self.assertIsNone(payload_default['keep_alive'])

if __name__ == "__main__":
    unittest.main()
