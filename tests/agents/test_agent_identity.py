import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.rossini import Rossini
from famiglia_core.agents.alfredo import Alfredo

@pytest.fixture
def mock_db_dependencies(mocker):
    mocker.patch("famiglia_core.db.agents.context_store.context_store.enabled", False)
    mocker.patch("famiglia_core.agents.souls.soul_registry.load_agent_soul", return_value="Test Soul")
    mocker.patch("famiglia_core.agents.souls.soul_registry.resolve_agent_id", side_effect=lambda agent_name, agent_id: agent_id or agent_name.lower().replace("dr. ", "").strip())
    # Mock PostgresCheckpointer to avoid DB connection
    mocker.patch("famiglia_core.db.observability.checkpointer.PostgresCheckpointer", return_value=MagicMock())

def test_rossini_agent_id_consistency(mock_db_dependencies, mocker):
    """Verify that Rossini uses 'rossini' (agent_id) and not 'Dr. Rossini' (name) for dispatching."""
    agent = Rossini()
    
    # Mock the ResponseDistributor
    mock_distributor = mocker.patch("famiglia_core.command_center.backend.api.services.response_distributor.ResponseDistributor.dispatch")
    
    # Mock final state for _finalize_response
    state = {
        "final_response": "Hello from the lab",
        "conversation_key": "test-key",
        "metadata": {"slack_channel": "C123"}
    }
    
    agent._finalize_response(state)
    
    # Check that dispatch was called with 'rossini'
    mock_distributor.assert_called_once()
    args, kwargs = mock_distributor.call_args
    assert kwargs["agent_id"] == "rossini"
    assert kwargs["agent_id"] != "Dr. Rossini"

def test_alfredo_agent_id_consistency(mock_db_dependencies, mocker):
    """Verify that Alfredo uses 'alfredo' for dispatching."""
    agent = Alfredo()
    mock_distributor = mocker.patch("famiglia_core.command_center.backend.api.services.response_distributor.ResponseDistributor.dispatch")
    
    state = {
        "final_response": "How can I serve you?",
        "conversation_key": "test-key",
        "metadata": {}
    }
    
    agent._finalize_response(state)
    
    kwargs = mock_distributor.call_args.kwargs
    assert kwargs["agent_id"] == "alfredo"

def test_base_agent_audit_logging_uses_id(mock_db_dependencies, mocker):
    """Verify that audit logging uses agent_id."""
    agent = Rossini()
    mock_audit = mocker.patch("famiglia_core.db.agents.audit.audit_logger.log_action")
    
    # Trigger _get_initial_state which calls log_action
    agent._get_initial_state("test task", "user", "conv-1")
    
    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert kwargs["agent_name"] == "rossini"
