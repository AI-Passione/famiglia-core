import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.db.agents.context_store import AgentContextStore

@pytest.fixture
def store():
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool"):
        return AgentContextStore()

def test_get_available_capabilities(store):
    mock_cursor = MagicMock()
    
    # Mocking contextual session entry
    store.db_session = MagicMock()
    store.db_session.return_value.__enter__.return_value = mock_cursor
    
    # Setup mock returns for 3 queries (tools, skills, workflows)
    mock_cursor.fetchall.side_effect = [
        [{"id": 1, "name": "web_search"}], # tools
        [{"id": 10, "name": "Python"}],     # skills
        [{"id": 100, "name": "Onboarding"}] # workflows
    ]
    
    result = store.get_available_capabilities()
    
    assert len(result["tools"]) == 1
    assert result["tools"][0]["name"] == "web_search"
    assert len(result["skills"]) == 1
    assert len(result["workflows"]) == 1
    assert mock_cursor.execute.call_count == 3

def test_update_agent_traits_sync(store):
    mock_cursor = MagicMock()
    store.db_session = MagicMock()
    store.db_session.return_value.__enter__.return_value = mock_cursor
    
    with patch("psycopg2.extras.execute_values") as mock_exec_values:
        success = store.update_agent_traits("alfredo", "tools", [1, 2, 3])
        
        assert success is True
        # Check DELETE was called
        assert "DELETE FROM agent_tools" in mock_cursor.execute.call_args_list[0][0][0]
        # Check execute_values was called for 3 items
        assert mock_exec_values.called
        args = mock_exec_values.call_args[0]
        assert len(args[2]) == 3 # values list length

def test_list_famiglia_agents_schema(store):
    mock_cursor = MagicMock()
    store.db_session = MagicMock()
    store.db_session.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        {
            "agent_id": "alfredo",
            "name": "Alfredo",
            "is_active": True,
            "skill_ids": [1],
            "tool_ids": [2],
            "workflow_ids": [3]
        }
    ]
    
    agents = store.list_famiglia_agents()
    assert len(agents) == 1
    assert agents[0]["is_active"] is True
    assert agents[0]["tool_ids"] == [2]
