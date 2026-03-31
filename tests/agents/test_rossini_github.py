import unittest
from unittest.mock import patch, MagicMock
from famiglia_core.agents.rossini import Rossini
import json

MOCK_MILESTONES = {
    "Milestone 1: Auth": "Implement JWT login",
    "Milestone 2: UI": "Implement new dashboard"
}

APPROVED_PRD_BLOCKS = [
    {"type": "paragraph", "text": {"content": "Milestone 1: Auth"}},
    {"type": "paragraph", "text": {"content": "- Implement JWT login"}}
]

class TestRossiniGitHub(unittest.TestCase):
    def setUp(self):
        self.rossini = Rossini()

    def test_tool_registration(self):
        """Verify GitHub tools are in the registry."""
        tools = self.rossini.tools
        self.assertIn("manage_github_issue", tools)
        self.assertIn("manage_github_pull_request", tools)
        self.assertIn("manage_github_milestone", tools)
        self.assertIn("list_accessible_repos", tools)

    @patch("famiglia_core.agents.orchestration.features.milestone_creation.notion_client")
    @patch("famiglia_core.agents.orchestration.features.milestone_creation.github_client")
    @patch("famiglia_core.agents.orchestration.features.milestone_creation.github_store")
    @patch("famiglia_core.agents.orchestration.features.milestone_creation.client")
    @patch("famiglia_core.agents.orchestration.features.milestone_creation.slack_queue")
    def test_milestone_creation_logic(self, mock_slack, mock_llm, mock_store, mock_github, mock_notion):
        """Verify the milestone creation flow succeeds."""
        workflow = self.rossini.milestone_creation_graph

        mock_notion.read_page.return_value = {
            "blocks": APPROVED_PRD_BLOCKS,
            "page_properties": {"title": "PRD: Test Feature [Approved]"},
            "url": "https://notion.so/test",
        }

        mock_store.get_repo_for_prd.return_value = {"repo_name": "la-passione-inc/test", "github_repo_id": 1}
        mock_github.get_node_ids.return_value = {"repository_id": "r1", "owner_id": "o1", "owner_type": "Organization"}

        # LLM calls: 1. Select repo, 2. Parse plan, 3. Semantic Mapping
        mock_llm.complete.side_effect = [
            ("la-passione-inc/test", {}),          # select_repo
            (json.dumps(MOCK_MILESTONES), {}),     # parse_prd_into_plan
            (json.dumps({"milestones": {}, "issues": {}}), {}), # semantic_mapping
        ]

        mock_github.list_milestones.return_value = []
        mock_github.list_issues.return_value = []
        mock_github.create_milestone.return_value = {"number": 1}
        mock_github.create_issue.return_value = {"number": 10, "node_id": "i10"}

        state = {"notion_page_id": "p123", "task": "Sync"}
        workflow.invoke(state, config={"configurable": {"thread_id": "t1"}})

        self.assertEqual(mock_github.create_milestone.call_count, 1)
        self.assertEqual(mock_github.create_issue.call_count, 1)

if __name__ == "__main__":
    unittest.main()
