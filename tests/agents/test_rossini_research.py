import unittest
from unittest.mock import patch, MagicMock
from famiglia_core.agents.rossini import Rossini

class TestRossiniResearch(unittest.TestCase):
    def setUp(self):
        self.patcher_notion = patch("famiglia_core.agents.orchestration.features.market_research.notion_client")
        self.patcher_web = patch("famiglia_core.agents.orchestration.features.market_research.web_search_client")
        self.patcher_slack = patch("famiglia_core.agents.orchestration.features.market_research.slack_queue")
        self.patcher_llm = patch("famiglia_core.agents.orchestration.features.market_research.client")
        
        self.mock_notion = self.patcher_notion.start()
        self.mock_web = self.patcher_web.start()
        self.mock_slack = self.patcher_slack.start()
        self.mock_llm = self.patcher_llm.start()
        
        # Mock LLM response
        self.mock_llm.complete.return_value = ("Mocked LLM Content", "mock-model")
        
        # Mock Notion creation
        self.mock_notion.create_page.return_value = "Successfully created Notion page 'Test' with ID: 123. URL: http://notion.so/test"
        
        self.rossini = Rossini()

    def tearDown(self):
        self.patcher_notion.stop()
        self.patcher_web.stop()
        self.patcher_slack.stop()
        self.patcher_llm.stop()

    def test_graph_initialization(self):
        """Verify the research graph is initialized in Rossini."""
        self.assertIsNotNone(self.rossini.research_graph)

    def test_run_market_research_flow(self):
        """Verify the full graph execution flow."""
        with patch.object(self.rossini, "propose_action", return_value=True):
            topic = "AI Agents in Fashion"
            result = self.rossini.run_market_research(topic)
            
            # Verify calls
            self.mock_web.search.assert_called_once()
            self.mock_notion.create_page.assert_called_once()
            self.mock_slack.post_message.assert_called_once()
            
            self.assertIn("I have completed the market research", result)
            self.assertIn("AI Agents in Fashion", result)
            self.assertIn("http://notion.so/test", result)

    def test_auto_trigger_logic(self):
        """Verify complete_task triggers market research when keywords are present."""
        with patch.object(self.rossini, "run_market_research") as mock_run:
            mock_run.return_value = "Research triggered"
            
            # Test simple triggers
            self.rossini.complete_task("Perform market research on Italian leather trends")
            mock_run.assert_called_with("Italian leather trends")
            
            mock_run.reset_mock()
            self.rossini.complete_task("Hey research on Milan fashion week please")
            mock_run.assert_called_with("Milan fashion week please")

    def test_notion_retry_loop(self):
        """Verify the graph retries Notion saves on failure."""
        with patch.object(self.rossini, "propose_action", return_value=True):
            # Mock Notion to fail twice then succeed
            self.mock_notion.create_page.side_effect = [
                Exception("Validation Error 400"),
                Exception("Validation Error 400"),
                "Successfully created Notion page 'Test' with ID: 789. URL: http://notion.so/fixed"
            ]
            
            topic = "Retry Test"
            result = self.rossini.run_market_research(topic)
            
            # Should have called create_page 3 times (1 original + 2 retries)
            self.assertEqual(self.mock_notion.create_page.call_count, 3)
            self.assertIn("fixed", result)

    def test_search_retry_loop(self):
        """Verify the graph retries search on failure with refinement."""
        with patch.object(self.rossini, "propose_action", return_value=True):
            self.mock_web.search.side_effect = [
                "Error: API Timeout",
                "Error: No results found",
                "Fixed Search Results content"
            ]
            
            topic = "Search Retry Test"
            result = self.rossini.run_market_research(topic)
            
            # Should have called search 3 times
            self.assertEqual(self.mock_web.search.call_count, 3)
            self.assertIn("Search Retry Test", result)

if __name__ == "__main__":
    unittest.main()
