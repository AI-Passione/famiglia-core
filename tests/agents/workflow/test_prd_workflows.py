import sys
import os
from unittest.mock import MagicMock, patch
import json

# Add src to path
sys.path.append(os.getcwd())

from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.orchestration.features.prd_review import PRDReviewState
from famiglia_core.agents.orchestration.features.milestone_creation import MilestoneCreationState
import langgraph

def test_prd_review_logic():
    rossini = Rossini()
    workflow = rossini.prd_review_graph
    
    # Mock Notion tools
    with patch("famiglia_core.agents.orchestration.features.prd_review.notion_client") as mock_notion:
        mock_notion.read_page.return_value = {
            "blocks": ["# PRD: Test", "Status: Unverified"],
            "page_properties": {"title": "Test PRD"}
        }
        mock_notion.list_comments.return_value = [
            {"text": "Add a section on security", "id": "c1"}
        ]
        mock_notion.append_text_to_page.return_value = "Success"
        
        # Invoke workflow
        state = {
            "notion_page_id": "test_id",
            "task": "Review comments",
            "slack_channel": "C0AL8GW2VAL"
        }
        config = {"configurable": {"thread_id": "test"}}
        
        # Test just the load node if full graph is too heavy for unit test
        print("Testing PRD Review logic...")
        final_state = workflow.invoke(state, config=config)
        
        assert "feedback_summary" in final_state
        assert "evaluation_results" in final_state
        assert "updated_prd_markdown" in final_state
        assert final_state["notion_success"] is True
        
        # Verify comment creation was called (at least once for the reply)
        assert mock_notion.create_comment.called
        print("SUCCESS: PRD Review workflow logic (including replies) verified.")

def test_milestone_creation_logic():
    import json as _json
    rossini = Rossini()
    workflow = rossini.milestone_creation_graph

    mock_milestones = [
        {
            "title": "Milestone 1: Core",
            "description": "Core feature delivery.",
            "issues": [
                {"title": "Implement auth", "body": "Build auth endpoint."},
                {"title": "Setup database", "body": "Schema and migrations."},
            ],
        }
    ]

    with patch("famiglia_core.agents.orchestration.features.milestone_creation.notion_client") as mock_notion, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.github_client") as mock_github, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.github_store") as mock_store, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.client") as mock_llm, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.slack_queue"), \
         patch.object(rossini, "list_accessible_repos", return_value="la-passione-inc/test"):

        mock_notion.read_page.return_value = {
            "blocks": ["# PRD: Test"],
            "page_properties": {"title": "Test PRD [Approved]"},
            "url": "https://notion.so/test",
        }

        # No cached mapping -> LLM selects repo first, then parses plan
        mock_store.get_repo_for_prd.return_value = None
        mock_store.upsert_prd_repo_mapping.return_value = True

        mock_llm.complete.side_effect = [
            ("la-passione-inc/test", {}),
            (_json.dumps(mock_milestones), {}),
        ]

        # GitHub: nothing pre-existing
        mock_github.list_milestones.return_value = []
        mock_github.list_issues.return_value = []
        mock_github.create_milestone.return_value = {"number": 1, "title": "Milestone 1: Core"}
        mock_github.create_issue.return_value = {"number": 10, "title": "Implement auth"}

        state = {
            "notion_page_id": "test_id",
            "task": "Create milestones",
            "slack_channel": "C0AL8GW2VAL"
        }
        config = {"configurable": {"thread_id": "test2"}}

        print("Testing Milestone Creation logic...")
        final_state = workflow.invoke(state, config=config)

        assert "milestones" in final_state
        assert "issues" in final_state
        assert "repo_name" in final_state
        assert len(final_state["creation_results"]) > 0
        print("SUCCESS: Milestone Creation workflow logic verified.")

if __name__ == "__main__":
    test_prd_review_logic()
    test_milestone_creation_logic()
