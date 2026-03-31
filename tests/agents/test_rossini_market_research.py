import unittest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.orchestration.features.market_research import MarketResearchState

class TestRossiniMarketResearch(unittest.TestCase):
    def setUp(self):
        # We need to mock environment variables and external clients
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
            # Should have called LLM for fixing twice
            # curate_results (1) + fix_notion_error (2) + generate_ideas (1) + notify_slack (1) = 5
            # Actually, fix_notion_error is called for each retry.
            # Total LLM calls: curate (1) + fix (2) + ideas (1) + slack (1) = 5
            self.assertEqual(self.mock_llm.complete.call_count, 5)
            
            self.assertIn("fixed", result)
            self.assertIn("Full Report saved to Notion", result)

    def test_notion_failure_exhaustion(self):
        """Verify the graph continues after 3 failed Notion attempts."""
        with patch.object(self.rossini, "propose_action", return_value=True):
            # Force failure for all calls
            self.mock_notion.create_page.side_effect = Exception("Permanent Error")
            
            topic = "Failure Test"
            result = self.rossini.run_market_research(topic)
            
            # 1 initial + 2 retries = 3 calls total
            self.assertEqual(self.mock_notion.create_page.call_count, 3)
            self.assertIn("failed after 3 attempts", result)
            
            # Verify Slack message contains the failure warning
            # The summary_prompt should have received the failure status
            # Slack message should reflect it
            self.mock_slack.post_message.assert_called_once()
            call_args = self.mock_slack.post_message.call_args[1]
            # Since LLM generates the slack message, we check if the notion_status was passed to LLM
            # We can't easily check the final slack msg content because LLM is mocked to return "Mocked LLM Content"
            # But we can verify transition to notify_slack happened.

    def test_search_retry_loop(self):
        """Verify the graph retries search on failure with refinement."""
        with patch.object(self.rossini, "propose_action", return_value=True):
            # Mock web search to fail twice then succeed
            # First attempt returns error, second returns error, third returns success
            from unittest.mock import MagicMock
            self.mock_web.search.side_effect = [
                "Error: API Timeout",
                "Error: No results found",
                "Fixed Search Results content"
            ]
            
            topic = "Search Retry Test"
            result = self.rossini.run_market_research(topic)
            
            # Should have called search 3 times
            self.assertEqual(self.mock_web.search.call_count, 3)
            # Should have called LLM for refinement twice
            # curate (1) + refine (2) + ideas (1) + slack (1) = 5
            self.assertEqual(self.mock_llm.complete.call_count, 5)
            
            self.assertIn("Search Retry Test", result)

    def test_search_failure_exhaustion(self):
        """Verify the graph continues even if search fails 3 times."""
        with patch.object(self.rossini, "propose_action", return_value=True):
            self.mock_web.search.side_effect = Exception("Internal Search Error")
            
            topic = "Search Fail Test"
            result = self.rossini.run_market_research(topic)
            
            # 3 attempts
            self.assertEqual(self.mock_web.search.call_count, 3)
            # Curation should still happen and report will be generated (even if search results are error strings)
            self.assertIn("Search Fail Test", result)

if __name__ == "__main__":
    unittest.main()
