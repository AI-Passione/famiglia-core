import pytest
from unittest.mock import patch, MagicMock
import json
from src.db.audit import AuditLogger

@pytest.fixture
def mock_conn():
    with patch('psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        yield mock_conn

def test_log_action_creates_record(mock_conn):
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = (1,) # Mock returning the ID
    
    logger = AuditLogger()
    action_id = logger.log_action(
        agent_name="Alfredo",
        action_type="DelegateTask",
        action_details={"target": "Riccado", "task": "Review PR"},
        is_approval_required=True
    )
    
    assert action_id == 1
    mock_conn.cursor.assert_called_once()
    mock_cursor.execute.assert_called_once()
    assert "INSERT INTO agent_actions" in mock_cursor.execute.call_args[0][0]
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_update_approval(mock_conn):
    mock_cursor = mock_conn.cursor.return_value
    
    logger = AuditLogger()
    logger.update_approval(1, "APPROVED")
    
    mock_cursor.execute.assert_called_once()
    assert "UPDATE agent_actions" in mock_cursor.execute.call_args[0][0]
    assert "APPROVED" in mock_cursor.execute.call_args[0][1]
    mock_conn.commit.assert_called_once()
