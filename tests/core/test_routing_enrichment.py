import unittest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.base_agent import BaseAgent

class TestRoutingEnrichment(unittest.TestCase):
    def setUp(self):
        self.model_config = {
            "primary": "gemma3:4b",
            "lite": "gemma3:1b",
            "secondary": "qwen2.5:3b",
            "WORKFLOW": "llama3.1:8b",
            "TOOL": "llama3.1:8b"
        }
        self.agent = BaseAgent(name="Alfredo", role="Orchestrator", model_config=self.model_config)

    @patch("famiglia_core.agents.base_agent.client.complete")
    def test_routing_chat(self, mock_complete):
        # Case 1: Fast-path Greeting
        self.assertEqual(self.agent._get_routing_mode("hi"), "CHAT")
        self.assertEqual(self.agent._get_routing_mode("ciao!"), "CHAT")
        
        # Case 2: LLM fallback to CHAT
        mock_complete.return_value = ("CHAT", "gemma3:1b")
        self.assertEqual(self.agent._get_routing_mode("how are you?"), "CHAT")

    @patch("famiglia_core.agents.base_agent.client.complete")
    def test_routing_search(self, mock_complete):
        # Case 1: Fast-path Search
        self.assertEqual(self.agent._get_routing_mode("search for news"), "SEARCH")
        
        # Case 2: LLM fallback to SEARCH
        mock_complete.return_value = ("SEARCH", "gemma3:1b")
        self.assertEqual(self.agent._get_routing_mode("find the latest trends"), "SEARCH")

    @patch("famiglia_core.agents.base_agent.client.complete")
    def test_routing_tool(self, mock_complete):
        # Case 1: Fast-path Tool
        self.assertEqual(self.agent._get_routing_mode("list my github issues"), "TOOL")
        self.assertEqual(self.agent._get_routing_mode("notion list pages"), "TOOL")
        
        # Case 2: LLM fallback to TOOL
        mock_complete.return_value = ("TOOL", "gemma3:1b")
        self.assertEqual(self.agent._get_routing_mode("some generic tool request"), "TOOL")

    @patch("famiglia_core.agents.base_agent.client.complete")
    def test_routing_workflow(self, mock_complete):
        # Case 1: Fast-path Workflow
        self.assertEqual(self.agent._get_routing_mode("run github diagnostic"), "WORKFLOW")
        self.assertEqual(self.agent._get_routing_mode("check system access"), "WORKFLOW")
        
        # Case 2: LLM fallback to WORKFLOW
        mock_complete.return_value = ("WORKFLOW", "gemma3:1b")
        self.assertEqual(self.agent._get_routing_mode("verify my permissions and diagnostic state"), "WORKFLOW")

    @patch("famiglia_core.agents.base_agent.client.complete")
    def test_routing_complex(self, mock_complete):
        # Case 1: Fast-path Complex
        self.assertEqual(self.agent._get_routing_mode("analyze this code"), "COMPLEX")
        self.assertEqual(self.agent._get_routing_mode("lgtm"), "COMPLEX")
        
        # Case 2: LLM fallback to COMPLEX
        mock_complete.return_value = ("COMPLEX", "qwen2.5:3b")
        self.assertEqual(self.agent._get_routing_mode("write a plan for the new feature"), "COMPLEX")

if __name__ == "__main__":
    unittest.main()
