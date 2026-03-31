"""
Tests for the Milestone & Issue Creation workflow.
"""
import sys
import os
from unittest.mock import MagicMock, patch, call
import json

sys.path.append(os.getcwd())

from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.orchestration.features.milestone_creation import MilestoneCreationState

APPROVED_PRD_BLOCKS = [
    {"text": "# PRD: Test Feature"},
    {"text": "## Goals\nDeliver X by Q3."},
]

MOCK_MILESTONES = [
    {
        "title": "Milestone 1: Auth",
        "description": "Deliver authentication.",
        "issues": [
            {"title": "Implement JWT login", "body": "Build login endpoint."},
        ],
    },
]

# ---------------------------------------------------------------------------
# Test 1: Full happy path
# ---------------------------------------------------------------------------
def test_milestone_creation_logic():
    rossini = Rossini()
    workflow = rossini.milestone_creation_graph

    with patch("famiglia_core.agents.orchestration.features.milestone_creation.notion_client") as mock_notion, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.github_client") as mock_github, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.github_store") as mock_store, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.client") as mock_llm, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.slack_queue"), \
         patch.object(rossini, "list_accessible_repos", return_value="la-passione-inc/test"):

        mock_notion.read_page.return_value = {
            "blocks": APPROVED_PRD_BLOCKS,
            "page_properties": {"title": "PRD: Test Feature [Approved]"},
            "url": "https://notion.so/test",
        }

        mock_store.get_repo_for_prd.return_value = None
        mock_store.upsert_prd_repo_mapping.return_value = True

        mock_github.get_node_ids.return_value = {"repository_id": "r1", "owner_id": "o1", "owner_type": "Organization"}

        # LLM calls: 1. Select repo, 2. Parse plan, 3. Semantic Mapping
        mock_llm.complete.side_effect = [
            ("la-passione-inc/test", {}),          # select_repo
            (json.dumps(MOCK_MILESTONES), {}),     # parse_prd_into_plan
            (json.dumps({"milestones": {}, "issues": {}}), {}), # semantic_mapping (nothing found)
        ]

        mock_github.list_milestones.return_value = []
        mock_github.list_issues.return_value = []
        mock_github.create_milestone.return_value = {"number": 1}
        mock_github.create_issue.return_value = {"number": 10, "node_id": "i10"}

        state = {"notion_page_id": "p123", "task": "Sync"}
        workflow.invoke(state, config={"configurable": {"thread_id": "t1"}})

        assert mock_github.create_milestone.call_count == 1
        assert mock_github.create_issue.call_count == 1
        print("PASSED: test_milestone_creation_logic")


# ---------------------------------------------------------------------------
# Test 2: Semantic Issue Matching – different milestone names
# ---------------------------------------------------------------------------
def test_semantic_issue_matching_different_milestones():
    rossini = Rossini()
    workflow = rossini.milestone_creation_graph

    with patch("famiglia_core.agents.orchestration.features.milestone_creation.notion_client") as mock_notion, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.github_client") as mock_github, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.github_store") as mock_store, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.client") as mock_llm, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.slack_queue"), \
         patch.object(rossini, "list_accessible_repos", return_value="la-passione-inc/test"):

        mock_notion.read_page.return_value = {
            "blocks": APPROVED_PRD_BLOCKS,
            "page_properties": {"title": "PRD: Test Feature [Approved]"},
            "url": "https://notion.so/test",
        }

        mock_store.get_repo_for_prd.return_value = {"repo_name": "la-passione-inc/test", "github_repo_id": 1}
        mock_github.get_node_ids.return_value = {"repository_id": "r1", "owner_id": "o1", "owner_type": "Organization"}

        # Planned: "Milestone 1: Auth" -> "Implement JWT login"
        # Existing: "Authentication" -> "JWT Implementation"
        mock_llm.complete.side_effect = [
            (json.dumps(MOCK_MILESTONES), {}),     # parse_prd_into_plan
            (json.dumps({
                "milestones": {"Milestone 1: Auth": 5},
                "issues": {"Implement JWT login": 101}
            }), {}) 
        ]

        # In GitHub, the issue is there but milestone title is different
        mock_github.list_milestones.return_value = [{"title": "Authentication", "number": 5}]
        mock_github.list_issues.return_value = [{"title": "JWT Implementation", "number": 101, "milestone_title": "Authentication"}]

        state = {"notion_page_id": "p123", "task": "Sync"}
        final_state = workflow.invoke(state, config={"configurable": {"thread_id": "t2"}})

        # Should skip both due to semantic match and include aggregated URLs
        assert any("⏭️ Milestone already exists: <https://github.com/la-passione-inc/test/milestone/5|*Milestone 1: Auth*>" in r for r in final_state["creation_results"])
        assert any("_Issues: <https://github.com/la-passione-inc/test/issues/101|#101>_" in r for r in final_state["creation_results"])
        
        # Verify counts in final response
        assert "2 items synced (2 existing, 0 new)" in final_state["final_response"]
        
        mock_github.create_milestone.assert_not_called()
        mock_github.create_issue.assert_not_called()
        print("PASSED: test_semantic_issue_matching_different_milestones")


def test_milestone_hallucination_validation():
    """Verify that hallucinated milestone numbers are caught and nullified."""
    rossini = Rossini()
    from famiglia_core.agents.orchestration.features.milestone_creation import MilestoneCreationWorkflow
    workflow_logic = MilestoneCreationWorkflow(rossini)

    with patch("famiglia_core.agents.orchestration.features.milestone_creation.github_client") as mock_github, \
         patch("famiglia_core.agents.orchestration.features.milestone_creation.client") as mock_llm:

        # 1. Existing milestones are #1
        mock_github.list_milestones.return_value = [{"title": "Existing", "number": 1}]
        mock_github.list_issues.return_value = [{"title": "Issue 62", "number": 62}] # Issue 62 exists
        
        # 2. LLM hallucinates #62 as a milestone match
        mock_llm.complete.return_value = ('{"milestones": {"Milestone 1: Auth": 62}, "issues": {}}', None)
        
        state = {
            "repo_name": "la-passione-inc/test",
            "milestones": [{"title": "Milestone 1: Auth", "description": "Auth desc", "issues": []}],
            "issues": [{"title": "Issue 1", "body": "Body 1", "_milestone_title": "Milestone 1: Auth"}],
            "semantic_mapping": {}
        }
        
        # Call the node directly
        result = workflow_logic.check_existing(state)
        
        # Mapping for "Milestone 1: Auth" should be None because #62 is not a valid milestone
        assert result["semantic_mapping"]["milestones"]["Milestone 1: Auth"] is None
        print("PASSED: test_milestone_hallucination_validation")


if __name__ == "__main__":
    test_milestone_creation_logic()
    test_semantic_issue_matching_different_milestones()
    test_milestone_hallucination_validation()
    print("\n✅ Issue Sync tests passed.")
