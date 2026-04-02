import pytest
import unittest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.base_agent import BaseAgent

# --- Routing Enrichment Tests ---

@pytest.fixture
def mock_agent_deps_core():
    with patch("famiglia_core.agents.base_agent.load_agent_soul", return_value="Test soul"), \
         patch("famiglia_core.agents.base_agent.resolve_agent_id", return_value="test_agent"):
        yield

def test_base_agent_initialization(mock_agent_deps_core):
    agent = BaseAgent(name="Alfredo", role="Orchestrator", model_config={"primary": "gpt-4"})
    assert agent.name == "Alfredo"
    assert hasattr(agent, "graph")

def test_base_agent_complete_task_dispatch(mock_agent_deps_core):
    agent = BaseAgent(name="Alfredo", role="Orchestrator", model_config={"primary": "gpt-4"})
    # Mock the graph stream for core dispatch verification
    with patch.object(agent.graph, "stream") as mock_stream:
        mock_stream.return_value = [{"final_response": "Hello", "used_model": "gpt-4", "conversation_key": "test"}]
        res = agent.complete_task("Hi")
        assert "Hello" in res
        assert mock_stream.called

# --- Task Helpers & Utilities ---

def test_utility_truncation():
    from famiglia_core.agents.utils.agent_utils import truncate
    assert truncate("Hello World", 5) == "He..."
