import pytest
from unittest.mock import patch, MagicMock
from famiglia_core.db.agents.audit import AuditLogger

@pytest.fixture
def mock_db_session():
    with patch("famiglia_core.db.agents.audit.context_store.db_session") as mock_session:
        mock_cursor = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_cursor
        yield mock_cursor

def test_audit_log_action(mock_db_session):
    mock_db_session.fetchone.return_value = {"id": 1}
    
    logger = AuditLogger()
    action_id = logger.log_action(
        agent_name="Alfredo",
        action_type="DelegateTask",
        action_details={"target": "Riccardo", "task": "Review PR"},
        is_approval_required=True
    )
    
    assert action_id == 1
    assert "INSERT INTO agent_actions" in mock_db_session.execute.call_args[0][0]

def test_audit_update_approval(mock_db_session):
    logger = AuditLogger()
    logger.update_approval(1, "APPROVED")
    
    # Check if execute was called with correct SQL
    assert "UPDATE agent_actions" in mock_db_session.execute.call_args[0][0]
    assert "APPROVED" in mock_db_session.execute.call_args[0][1]
