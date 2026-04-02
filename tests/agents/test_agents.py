import pytest
import json
from unittest.mock import MagicMock, patch
from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.db.agents.context_store import AgentContextStore

# --- Base Agent & Context Tests ---

@pytest.fixture
def mock_agent_deps():
    with patch("famiglia_core.agents.base_agent.load_agent_soul", return_value="You are a test agent."), \
         patch("famiglia_core.agents.base_agent.resolve_agent_id", return_value="test_agent"), \
         patch("famiglia_core.agents.base_agent.context_store") as mock_store, \
         patch("famiglia_core.agents.base_agent.audit_logger") as mock_audit:
        yield {"store": mock_store, "audit": mock_audit}

def test_agent_complete_task_logic(mock_agent_deps):
    agent = BaseAgent(
        name="Alfredo",
        role="Agent orchestrator",
        model_config={"primary": "gemini-2.0-flash"},
    )
    
    # Mock the graph stream to simulate a mission update flow
    with patch.object(agent.graph, "stream") as mock_stream:
        mock_stream.return_value = [
            {
                "final_response": "Task completed successfully.",
                "used_model": "gemini-2.0-flash",
                "conversation_key": "test_conv",
                "metadata": {}
            }
        ]
        
        response = agent.complete_task("Do something.", sender="Don Jimmy")
        assert "Task completed successfully." in response

def test_context_store_logging():
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool") as mock_pool_class:
        mock_pool = mock_pool_class.return_value
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_cursor = MagicMock()
        # Mocking the context manager entry for the cursor
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 101}

        store = AgentContextStore()
        msg_id = store.log_message(
            agent_name="Alfredo",
            conversation_key="test_conv",
            role="user",
            content="Hello",
            sender="Jimmy"
        )
        assert msg_id == 101

def test_list_famiglia_agents_returns_joined_roster_rows():
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool") as mock_pool_class:
        mock_pool = mock_pool_class.return_value
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {
                "id": "alfredo",
                "agent_id": "alfredo",
                "name": "Alfredo",
                "role": "Strategic Lead",
                "status": "active",
                "aliases": ["Chief of Staff"],
                "personality": "Calm and precise",
                "identity": "Coordinates the family.",
                "skills": ["Coordination"],
                "tools": ["github"],
                "workflows": ["Command Center"],
                "latest_conversation_snippet": "Status confirmed.",
                "last_active": None,
            }
        ]

        store = AgentContextStore()
        rows = store.list_famiglia_agents()

        assert len(rows) == 1
        assert rows[0]["agent_id"] == "alfredo"
        executed_sql = mock_cursor.execute.call_args[0][0]
        assert "FROM agents a" in executed_sql
        assert "LEFT JOIN archetypes ar" in executed_sql
        assert "latest_messages" in executed_sql

def test_list_famiglia_agents_handles_query_failure():
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool") as mock_pool_class:
        mock_pool = mock_pool_class.return_value
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("query failed")

        store = AgentContextStore()

        assert store.list_famiglia_agents() == []
