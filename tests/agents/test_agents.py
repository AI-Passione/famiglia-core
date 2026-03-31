import pytest
import json
from unittest.mock import MagicMock, patch
from famiglia_core.agents.base_agent import BaseAgent
from famiglia_core.agents.riccado import Riccado
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
    
    # Mock the graph invoke to simulate a simple response
    with patch.object(agent.graph, "invoke") as mock_invoke:
        mock_invoke.return_value = {
            "final_response": "Task completed successfully.",
            "used_model": "gemini-2.0-flash",
            "conversation_key": "test_conv",
            "metadata": {}
        }
        
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
